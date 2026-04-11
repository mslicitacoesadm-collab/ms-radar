from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any
import json
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import (
    PNCP_CONSULTA_BASE_URL,
    PNCP_CONNECT_TIMEOUT,
    PNCP_MAX_RETRIES,
    PNCP_READ_TIMEOUT,
    PNCP_RETRY_BACKOFF,
    REQUESTS_USER_AGENT,
)
from app.core.utils import pncp_date


class PNCPClientError(Exception):
    pass


@dataclass
class ProbeResult:
    ok: bool
    status_code: int | None
    elapsed_seconds: float | None
    message: str


class PNCPClient:
    def __init__(self, base_url: str = PNCP_CONSULTA_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.timeout = (PNCP_CONNECT_TIMEOUT, PNCP_READ_TIMEOUT)
        self.session = requests.Session()
        self.session.headers.update(
            {
                'accept': '*/*',
                'User-Agent': REQUESTS_USER_AGENT,
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
            }
        )
        retry = Retry(
            total=PNCP_MAX_RETRIES,
            connect=PNCP_MAX_RETRIES,
            read=PNCP_MAX_RETRIES,
            status=PNCP_MAX_RETRIES,
            status_forcelist=[408, 429, 500, 502, 503, 504],
            backoff_factor=PNCP_RETRY_BACKOFF,
            allowed_methods=['GET'],
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def _parse_error_message(self, response: requests.Response) -> str:
        try:
            payload = response.json()
            if isinstance(payload, dict):
                return payload.get('message') or payload.get('detail') or json.dumps(payload, ensure_ascii=False)[:500]
            return str(payload)[:500]
        except Exception:
            return response.text[:500] or f'HTTP {response.status_code}'

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        url = f'{self.base_url}{path}'
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise PNCPClientError(str(exc)) from exc

        if response.status_code == 204:
            return {'data': [], 'empty': True, 'totalPaginas': 0, 'numeroPagina': params.get('pagina', 1)}
        if response.status_code >= 400:
            raise PNCPClientError(self._parse_error_message(response))
        try:
            payload = response.json()
        except ValueError as exc:
            raise PNCPClientError(f'Resposta JSON inválida do PNCP: {exc}') from exc
        if not isinstance(payload, dict):
            return {'data': payload or [], 'empty': not payload, 'totalPaginas': 1, 'numeroPagina': params.get('pagina', 1)}
        return payload

    def probe(self) -> ProbeResult:
        start = time.perf_counter()
        today = date.today()
        try:
            payload = self.list_published(
                data_inicial=pncp_date(today),
                data_final=pncp_date(today),
                codigo_modalidade=6,
                pagina=1,
                tamanho_pagina=10,
            )
            elapsed = round(time.perf_counter() - start, 2)
            return ProbeResult(True, 200, elapsed, f"Conexão OK. Registros={payload.get('totalRegistros', 0)}")
        except Exception as exc:
            elapsed = round(time.perf_counter() - start, 2)
            return ProbeResult(False, None, elapsed, str(exc))

    def _common_params(self, *, pagina: int, tamanho_pagina: int, codigo_modalidade: int, **filters: Any) -> dict[str, Any]:
        params: dict[str, Any] = {
            'codigoModalidadeContratacao': int(codigo_modalidade),
            'pagina': int(pagina),
            'tamanhoPagina': max(10, int(tamanho_pagina)),
        }
        mappings = {
            'codigo_modo_disputa': 'codigoModoDisputa',
            'uf': 'uf',
            'codigo_municipio_ibge': 'codigoMunicipioIbge',
            'cnpj': 'cnpj',
            'codigo_unidade_administrativa': 'codigoUnidadeAdministrativa',
            'id_usuario': 'idUsuario',
        }
        for src, dst in mappings.items():
            value = filters.get(src)
            if value not in (None, ''):
                params[dst] = value
        return params

    def list_published(self, *, data_inicial: str, data_final: str, codigo_modalidade: int, pagina: int = 1, tamanho_pagina: int = 20, **filters: Any) -> dict[str, Any]:
        params = self._common_params(pagina=pagina, tamanho_pagina=tamanho_pagina, codigo_modalidade=codigo_modalidade, **filters)
        params['dataInicial'] = pncp_date(data_inicial)
        params['dataFinal'] = pncp_date(data_final)
        return self._get('/v1/contratacoes/publicacao', params)

    def list_open_proposals(self, *, data_final: str, codigo_modalidade: int, pagina: int = 1, tamanho_pagina: int = 20, **filters: Any) -> dict[str, Any]:
        params = self._common_params(pagina=pagina, tamanho_pagina=tamanho_pagina, codigo_modalidade=codigo_modalidade, **filters)
        params['dataFinal'] = pncp_date(data_final)
        return self._get('/v1/contratacoes/proposta', params)

    def get_opportunity_detail(self, *, cnpj: str, ano: int, sequencial: int) -> dict[str, Any]:
        payload = self._get(f'/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}', {})
        if not isinstance(payload, dict):
            raise PNCPClientError('Detalhe da contratação retornou formato inválido.')
        return payload
