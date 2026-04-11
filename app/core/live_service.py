from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from app.core.config import DEFAULT_MODALIDADES_SCAN, NICHOS_PRONTOS, PNCP_CACHE_TTL_SECONDS
from app.core.pncp_client import PNCPClient, PNCPClientError
from app.core.search_engine import apply_detail, compute_scores, expand_query, infer_nichos, normalize_summary_item
from app.core.utils import compact_keywords, fold_text, iso_date, money, normalize_text, parse_date, pncp_date


client = PNCPClient()


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _matches_query(row: dict[str, Any], query: str) -> bool:
    query = normalize_text(query)
    if not query:
        return True
    haystack = compact_keywords(
        row.get('objeto_compra'),
        row.get('resumo_objeto'),
        row.get('orgao_razao_social'),
        row.get('municipio_nome'),
        row.get('uf_sigla'),
        row.get('modalidade_nome'),
        ' '.join(row.get('nichos', [])),
    )
    tokens = [t for t in expand_query(query).split() if t]
    return all(token in haystack for token in tokens[:6]) if tokens else True


def _matches_filters(row: dict[str, Any], filters: dict[str, Any]) -> bool:
    if filters.get('uf') and row.get('uf_sigla') != filters['uf']:
        return False
    municipio = fold_text(filters.get('municipio'))
    if municipio and municipio not in fold_text(row.get('municipio_nome')):
        return False
    modalidade = filters.get('modalidade_codigo')
    if modalidade and int(row.get('modalidade_codigo') or 0) != int(modalidade):
        return False
    valor = float(row.get('valor_total_estimado') or 0)
    if float(filters.get('valor_min') or 0) > 0 and valor < float(filters['valor_min']):
        return False
    if float(filters.get('valor_max') or 0) > 0 and valor > float(filters['valor_max']):
        return False
    if filters.get('only_open') and not row.get('is_open_proposal'):
        return False
    if not _matches_query(row, str(filters.get('query') or '')):
        return False
    return True


def _sort_rows(rows: list[dict[str, Any]], sort_by: str) -> list[dict[str, Any]]:
    if sort_by == 'prazo':
        return sorted(rows, key=lambda r: (parse_date(r.get('data_encerramento_proposta')) or date.max, -float(r.get('oportunidade_score') or 0)))
    if sort_by == 'valor':
        return sorted(rows, key=lambda r: (-float(r.get('valor_total_estimado') or 0), -float(r.get('oportunidade_score') or 0)))
    if sort_by == 'recentes':
        return sorted(rows, key=lambda r: (r.get('data_publicacao_pncp') or '', float(r.get('oportunidade_score') or 0)), reverse=True)
    return sorted(rows, key=lambda r: (-float(r.get('oportunidade_score') or 0), parse_date(r.get('data_encerramento_proposta')) or date.max))


@st.cache_data(ttl=PNCP_CACHE_TTL_SECONDS, show_spinner=False)
def probe_connection_cached() -> dict[str, Any]:
    result = client.probe()
    return {
        'ok': result.ok,
        'status_code': result.status_code,
        'elapsed_seconds': result.elapsed_seconds,
        'message': result.message,
        'checked_at': pd.Timestamp.utcnow().isoformat(),
    }


@st.cache_data(ttl=PNCP_CACHE_TTL_SECONDS, show_spinner=False)
def fetch_live_notices(
    *,
    endpoint: str,
    query: str = '',
    uf: str = '',
    municipio: str = '',
    modalidade_codigo: int = 0,
    valor_min: float = 0.0,
    valor_max: float = 0.0,
    only_open: bool = False,
    days_back: int = 7,
    max_pages: int = 2,
    page_size: int = 20,
    limit: int = 50,
) -> dict[str, Any]:
    today = date.today()
    data_inicial = today - timedelta(days=max(0, _safe_int(days_back, 7) - 1))
    modalidades = [int(modalidade_codigo)] if modalidade_codigo else DEFAULT_MODALIDADES_SCAN
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    pages_read = 0

    for modalidade in modalidades:
        for pagina in range(1, _safe_int(max_pages, 2) + 1):
            try:
                if endpoint == 'proposta':
                    payload = client.list_open_proposals(
                        data_final=pncp_date(today),
                        codigo_modalidade=modalidade,
                        pagina=pagina,
                        tamanho_pagina=page_size,
                        uf=uf or None,
                    )
                else:
                    payload = client.list_published(
                        data_inicial=pncp_date(data_inicial),
                        data_final=pncp_date(today),
                        codigo_modalidade=modalidade,
                        pagina=pagina,
                        tamanho_pagina=page_size,
                        uf=uf or None,
                    )
            except PNCPClientError as exc:
                errors.append(f'{endpoint} modalidade={modalidade} página={pagina}: {exc}')
                break

            pages_read += 1
            items = payload.get('data', []) or []
            if not items:
                break
            for item in items:
                row = normalize_summary_item(item, endpoint=endpoint, fonte_data_referencia=iso_date(today))
                row['nichos'] = infer_nichos(row.get('objeto_compra'))
                if _matches_filters(
                    row,
                    {
                        'query': query,
                        'uf': uf,
                        'municipio': municipio,
                        'modalidade_codigo': modalidade_codigo,
                        'valor_min': valor_min,
                        'valor_max': valor_max,
                        'only_open': only_open,
                    },
                ):
                    rows.append(row)
            total_paginas = int(payload.get('totalPaginas') or 0)
            if total_paginas and pagina >= total_paginas:
                break
            if len(rows) >= limit * 2:
                break
        if len(rows) >= limit * 2:
            break

    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.get('numero_controle_pncp') or f"{row.get('orgao_cnpj')}::{row.get('ano_compra')}::{row.get('sequencial_compra')}"
        current = dedup.get(key)
        if current is None or float(row.get('oportunidade_score') or 0) > float(current.get('oportunidade_score') or 0):
            dedup[key] = row
    filtered_rows = list(dedup.values())
    filtered_rows = _sort_rows(filtered_rows, 'score')[:limit]
    return {
        'rows': filtered_rows,
        'errors': errors,
        'pages_read': pages_read,
        'count': len(filtered_rows),
        'endpoint': endpoint,
        'generated_at': pd.Timestamp.utcnow().isoformat(),
    }


@st.cache_data(ttl=PNCP_CACHE_TTL_SECONDS, show_spinner=False)
def get_notice_detail_cached(cnpj: str, ano: int, sequencial: int, base_row: dict[str, Any]) -> dict[str, Any]:
    detail = client.get_opportunity_detail(cnpj=cnpj, ano=ano, sequencial=sequencial)
    merged = apply_detail(base_row, detail)
    merged['nichos'] = infer_nichos(merged.get('objeto_compra'))
    merged.update(compute_scores(merged))
    return merged


def merge_endpoints(*payloads: dict[str, Any], sort_by: str = 'score', limit: int = 50) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for payload in payloads:
        rows.extend(payload.get('rows', []))
        errors.extend(payload.get('errors', []))
    dedup: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.get('numero_controle_pncp') or f"{row.get('orgao_cnpj')}::{row.get('ano_compra')}::{row.get('sequencial_compra')}"
        current = dedup.get(key)
        if current is None or float(row.get('oportunidade_score') or 0) > float(current.get('oportunidade_score') or 0):
            dedup[key] = row
    final_rows = _sort_rows(list(dedup.values()), sort_by)[:limit]
    return {'rows': final_rows, 'errors': errors, 'count': len(final_rows)}


def compute_dashboard_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    open_now = sum(1 for r in rows if r.get('is_open_proposal'))
    urgent = sum(1 for r in rows if (parse_date(r.get('data_encerramento_proposta')) or date.max) <= date.today() + timedelta(days=2))
    total_value = sum(float(r.get('valor_total_estimado') or 0) for r in rows)
    uf_counts: dict[str, int] = {}
    mod_counts: dict[str, int] = {}
    for row in rows:
        uf = row.get('uf_sigla') or '—'
        mod = row.get('modalidade_nome') or 'Não informada'
        uf_counts[uf] = uf_counts.get(uf, 0) + 1
        mod_counts[mod] = mod_counts.get(mod, 0) + 1
    top_uf = max(uf_counts, key=uf_counts.get) if uf_counts else '—'
    top_mod = max(mod_counts, key=mod_counts.get) if mod_counts else '—'
    return {
        'total': total,
        'open_now': open_now,
        'urgent': urgent,
        'valor_total': total_value,
        'top_uf': top_uf,
        'top_modalidade': top_mod,
    }


def build_export_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).copy()
    ordered = [
        'numero_controle_pncp', 'resumo_objeto', 'objeto_compra', 'orgao_razao_social', 'municipio_nome', 'uf_sigla',
        'modalidade_nome', 'data_publicacao_pncp', 'data_abertura_proposta', 'data_encerramento_proposta',
        'valor_total_estimado', 'oportunidade_score', 'urgencia_score', 'valor_score', 'risco_score',
        'link_sistema_origem', 'link_processo_eletronico', 'is_open_proposal'
    ]
    cols = [c for c in ordered if c in df.columns] + [c for c in df.columns if c not in ordered]
    return df[cols]


def format_query_summary(query: str, uf: str, municipio: str, only_open: bool, days_back: int) -> str:
    parts = [f'Janela: últimos {days_back} dia(s)']
    if query:
        parts.append(f'Termo: {query}')
    if uf:
        parts.append(f'UF: {uf}')
    if municipio:
        parts.append(f'Município: {municipio}')
    if only_open:
        parts.append('Somente abertas')
    return ' · '.join(parts)
