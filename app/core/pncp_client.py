from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

import requests

from .config import ASSETS_DIR, SETTINGS
from .models import Notice

MODALITY_MAP = {
    1: 'Leilão Eletrônico',
    2: 'Diálogo Competitivo',
    3: 'Concurso',
    4: 'Concorrência Eletrônica',
    5: 'Concorrência Presencial',
    6: 'Pregão Eletrônico',
    7: 'Pregão Presencial',
    8: 'Dispensa de Licitação',
    9: 'Inexigibilidade',
    10: 'Manifestação de Interesse',
    11: 'Pré-qualificação',
    12: 'Credenciamento',
    13: 'Leilão Presencial',
}


def _iso(d: date | datetime | str) -> str:
    if isinstance(d, str):
        return d[:10]
    return d.strftime('%Y-%m-%d')


def _pick_deadline(item: dict[str, Any]) -> str:
    for key in ('dataEncerramentoProposta', 'dataAberturaProposta', 'dataEncerramento', 'dataAbertura'):
        value = item.get(key)
        if value:
            return str(value)[:10]
    return ''


def _pick_opening(item: dict[str, Any]) -> str:
    for key in ('dataAberturaProposta', 'dataAbertura'):
        value = item.get(key)
        if value:
            return str(value)[:10]
    return ''


def normalize_item(item: dict[str, Any]) -> Notice:
    org = item.get('orgaoEntidade') or {}
    unit = item.get('unidadeOrgao') or {}
    modality_code = item.get('modalidadeId') or item.get('codigoModalidadeContratacao') or item.get('modalidadeNome')
    modality = MODALITY_MAP.get(modality_code, '') if isinstance(modality_code, int) else str(modality_code or '')
    ano = item.get('anoCompra') or 0
    seq = item.get('sequencialCompra') or 0
    cnpj = org.get('cnpj', '')
    numero = item.get('numeroCompra') or 'Sem número'
    object_text = item.get('objetoCompra') or item.get('objetoContratacao') or ''
    title = f"{modality or 'Contratação'} {numero} — {object_text}".strip()
    source_id = item.get('numeroControlePNCP') or f"{cnpj}-{ano}-{seq}"
    publication = str(item.get('dataPublicacaoPncp') or '')[:10]
    estimated = item.get('valorTotalEstimado') or item.get('valorTotalHomologado') or 0

    return Notice(
        source_id=str(source_id),
        title=title,
        object_text=object_text,
        agency=org.get('razaoSocial', ''),
        state=unit.get('ufSigla', ''),
        city=unit.get('municipioNome', ''),
        modality=modality,
        estimated_value=float(estimated or 0),
        publication_date=publication,
        deadline_date=_pick_deadline(item),
        opening_date=_pick_opening(item),
        source_url=(item.get('linkSistemaOrigem') or item.get('linkProcessoEletronico') or 'https://pncp.gov.br'),
        source_system='PNCP',
        pncp_cnpj=str(cnpj),
        pncp_ano=int(ano or 0),
        pncp_sequencial=int(seq or 0),
        situation=str(item.get('situacaoCompraNome') or item.get('situacaoCompra') or ''),
        raw_json=json.dumps(item, ensure_ascii=False),
    )


def fetch_open_notices(days_ahead: int = 30, page_size: int = 50, max_pages: int = 10, uf: str = '', modalidade: int | None = None) -> list[Notice]:
    base_url = SETTINGS.pncp_base_url
    url = f"{base_url}/v1/contratacoes/proposta"
    notices: list[Notice] = []
    data_final = _iso(date.today() + timedelta(days=days_ahead))

    for pagina in range(1, max_pages + 1):
        params = {
            'dataFinal': data_final,
            'pagina': pagina,
            'tamanhoPagina': page_size,
        }
        if uf:
            params['uf'] = uf
        if modalidade:
            params['codigoModalidadeContratacao'] = modalidade
        response = requests.get(url, params=params, timeout=SETTINGS.pncp_timeout)
        if response.status_code == 204:
            break
        response.raise_for_status()
        payload = response.json()
        rows = payload.get('data') or []
        if not rows:
            break
        notices.extend(normalize_item(item) for item in rows)
        if not payload.get('paginasRestantes'):
            break
    return notices


def fetch_notice_detail(cnpj: str, ano: int, sequencial: int) -> dict[str, Any]:
    url = f"{SETTINGS.pncp_base_url}/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}"
    response = requests.get(url, timeout=SETTINGS.pncp_timeout)
    response.raise_for_status()
    return response.json()


def load_demo_notices() -> list[Notice]:
    path = ASSETS_DIR / 'sample_notices.json'
    raw = json.loads(path.read_text(encoding='utf-8'))
    return [Notice(**item) for item in raw]
