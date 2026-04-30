from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
import json
import os

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PNCP_API_BASE = os.getenv('PNCP_API_BASE', 'https://pncp.gov.br/api/consulta')
DEFAULT_MODALITIES = {
    6: 'Pregão Eletrônico',
    4: 'Concorrência Eletrônica',
    8: 'Dispensa de Licitação',
    1: 'Concorrência',
    2: 'Tomada de Preços',
    3: 'Convite',
    5: 'Leilão',
    7: 'Concurso',
}
DEFAULT_HOME_MODALITIES = [6, 4, 8]
SAMPLE_FILE = Path(__file__).resolve().parent.parent / 'data' / 'sample_notices.json'


class PNCPError(Exception):
    pass


@dataclass
class FeedResult:
    notices: list[dict[str, Any]]
    source: str
    message: str


def _make_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        connect=2,
        read=2,
        status=2,
        allowed_methods=['GET'],
        status_forcelist=[408, 429, 500, 502, 503, 504],
        backoff_factor=0.4,
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    session.headers.update({
        'accept': 'application/json, text/plain, */*',
        'User-Agent': 'MS Radar/10.1',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
    })
    return session


def _safe_date(value: Any) -> str | None:
    if value in (None, ''):
        return None
    if isinstance(value, (date, datetime)):
        return value.strftime('%Y-%m-%d')
    text = str(value).strip()
    if not text:
        return None
    if 'T' in text:
        text = text.split('T', 1)[0]
    for fmt in ('%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.strptime(text, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return text[:10]


def _text(*values: Any) -> str:
    for value in values:
        if value not in (None, ''):
            return str(value).strip()
    return ''


def _float(value: Any) -> float | None:
    if value in (None, ''):
        return None
    try:
        return float(str(value).replace('.', '').replace(',', '.'))
    except Exception:
        try:
            return float(value)
        except Exception:
            return None


def _normalize_notice(item: dict[str, Any]) -> dict[str, Any]:
    orgao = item.get('orgaoEntidade') or {}
    unidade = item.get('unidadeOrgao') or {}
    municipio = item.get('municipioNome') or item.get('nomeMunicipioIbge') or unidade.get('municipioNome') or unidade.get('nomeMunicipioIbge')
    uf = item.get('ufSigla') or unidade.get('ufSigla') or item.get('uf')
    modalidade_codigo = item.get('codigoModalidadeContratacao')
    numero = _text(item.get('numeroControlePNCP'), item.get('numeroCompra'), item.get('sequencialCompra'))
    ano = _text(item.get('anoCompra'))
    title = _text(
        item.get('objetoCompra'),
        item.get('titulo'),
        item.get('descricao'),
        f"{DEFAULT_MODALITIES.get(modalidade_codigo, 'Licitação')} {numero}/{ano}".strip('/'),
    )
    source_url = _text(
        item.get('linkSistemaOrigem'),
        item.get('urlSistemaOrigem'),
        item.get('linkProcessoEletronico'),
        'https://pncp.gov.br',
    )
    return {
        'source_id': _text(item.get('numeroControlePNCP'), item.get('id'), numero or title),
        'title': title,
        'object_text': _text(item.get('objetoCompra'), item.get('informacaoComplementar'), item.get('descricao')),
        'agency': _text(orgao.get('razaoSocial'), orgao.get('nome'), unidade.get('nomeUnidade'), item.get('orgaoEntidadeRazaoSocial')),
        'state': _text(uf),
        'city': _text(municipio),
        'modality': _text(item.get('modalidadeNome'), DEFAULT_MODALITIES.get(modalidade_codigo), item.get('modalidade')),
        'estimated_value': _float(item.get('valorTotalEstimado'), item.get('valorEstimado'), item.get('valorTotalHomologado')),
        'publication_date': _safe_date(item.get('dataPublicacaoPncp'), item.get('dataPublicacao')),
        'deadline_date': _safe_date(item.get('dataEncerramentoProposta'), item.get('dataAberturaProposta'), item.get('dataEncerramento')),
        'source_url': source_url,
        'source_system': 'PNCP',
        'opening_date': _safe_date(item.get('dataAberturaProposta'), item.get('dataAbertura')),
        'situation': _text(item.get('situacaoCompraNome'), item.get('situacaoNome'), item.get('situacaoCompraId')), 
        'numero_controle_pncp': _text(item.get('numeroControlePNCP')),
    }


def load_sample_notices() -> list[dict[str, Any]]:
    data = json.loads(SAMPLE_FILE.read_text(encoding='utf-8'))
    return data if isinstance(data, list) else []


def probe_connection() -> tuple[bool, str]:
    session = _make_session()
    today = date.today().strftime('%Y-%m-%d')
    params = {
        'dataFinal': today,
        'codigoModalidadeContratacao': 6,
        'pagina': 1,
        'tamanhoPagina': 10,
    }
    try:
        resp = session.get(f'{PNCP_API_BASE}/v1/contratacoes/proposta', params=params, timeout=(3, 8))
        if resp.status_code < 400:
            return True, 'Conexão ao PNCP disponível.'
        return False, f'PNCP respondeu HTTP {resp.status_code}.'
    except Exception as exc:
        return False, f'PNCP indisponível no momento: {exc}'


def _fetch_endpoint(modality_code: int, page: int = 1, page_size: int = 10, uf: str | None = None) -> list[dict[str, Any]]:
    session = _make_session()
    params: dict[str, Any] = {
        'dataFinal': date.today().strftime('%Y-%m-%d'),
        'codigoModalidadeContratacao': modality_code,
        'pagina': page,
        'tamanhoPagina': max(10, int(page_size)),
    }
    if uf:
        params['uf'] = uf
    url = f'{PNCP_API_BASE}/v1/contratacoes/proposta'
    response = session.get(url, params=params, timeout=(3, 12))
    response.raise_for_status()
    payload = response.json()
    data = payload.get('data') if isinstance(payload, dict) else payload
    if not isinstance(data, list):
        return []
    return [_normalize_notice(item) for item in data]


def _deduplicate(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = item.get('source_id') or f"{item.get('title')}|{item.get('agency')}|{item.get('deadline_date')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def _sort_notices(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(item: dict[str, Any]) -> tuple:
        deadline = item.get('deadline_date') or '9999-12-31'
        value = item.get('estimated_value') or 0.0
        return (deadline, -float(value))
    return sorted(items, key=key)


def fetch_home_feed(limit: int = 18, uf: str | None = None) -> FeedResult:
    items: list[dict[str, Any]] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=len(DEFAULT_HOME_MODALITIES)) as executor:
        futures = [executor.submit(_fetch_endpoint, code, 1, 10, uf) for code in DEFAULT_HOME_MODALITIES]
        for future in as_completed(futures):
            try:
                items.extend(future.result())
            except Exception as exc:
                errors.append(str(exc))
    items = _sort_notices(_deduplicate(items))[:limit]
    if items:
        source = 'live'
        message = 'Licitações carregadas em tempo real do PNCP.'
        if errors:
            message += ' Algumas rotas retornaram instabilidade, mas a vitrine principal foi carregada.'
        return FeedResult(items, source, message)
    sample = load_sample_notices()[:limit]
    return FeedResult(sample, 'demo', 'PNCP indisponível no momento. Exibindo vitrine de demonstração para teste do sistema.')


def apply_filters(
    notices: list[dict[str, Any]],
    *,
    query: str = '',
    uf: str = '',
    city: str = '',
    modality: str = '',
    only_bahia: bool = False,
) -> list[dict[str, Any]]:
    q = query.strip().lower()
    filtered = []
    for item in notices:
        if only_bahia and item.get('state') != 'BA':
            continue
        if uf and item.get('state') != uf:
            continue
        if city and item.get('city') != city:
            continue
        if modality and item.get('modality') != modality:
            continue
        if q:
            haystack = ' '.join([
                str(item.get('title', '')),
                str(item.get('object_text', '')),
                str(item.get('agency', '')),
                str(item.get('city', '')),
            ]).lower()
            if q not in haystack:
                continue
        filtered.append(item)
    return _sort_notices(filtered)


def aggregate_by_key(notices: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    bucket: dict[str, int] = {}
    for item in notices:
        value = item.get(key) or 'Não informado'
        bucket[value] = bucket.get(value, 0) + 1
    rows = [{key: k, 'total': v} for k, v in bucket.items()]
    rows.sort(key=lambda row: (-row['total'], row[key]))
    return rows


def unique_values(notices: list[dict[str, Any]], key: str) -> list[str]:
    values = sorted({str(item.get(key)).strip() for item in notices if item.get(key)})
    return values


def days_to_deadline(item: dict[str, Any]) -> int | None:
    deadline = item.get('deadline_date')
    if not deadline:
        return None
    try:
        d = datetime.strptime(deadline[:10], '%Y-%m-%d').date()
        return (d - date.today()).days
    except Exception:
        return None


def top_urgent(notices: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    rows = [n for n in notices if days_to_deadline(n) is not None]
    return sorted(rows, key=lambda n: (days_to_deadline(n), -(n.get('estimated_value') or 0)))[:limit]


def top_value(notices: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    rows = [n for n in notices if n.get('estimated_value')]
    return sorted(rows, key=lambda n: n.get('estimated_value') or 0, reverse=True)[:limit]
