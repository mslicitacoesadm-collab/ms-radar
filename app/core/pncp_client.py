from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import (
    PNCP_BASE_URL,
    PNCP_CONNECT_TIMEOUT,
    PNCP_MAX_RETRIES,
    PNCP_READ_TIMEOUT,
    PNCP_RETRY_BACKOFF,
    REQUESTS_USER_AGENT,
)


class PNCPClientError(Exception):
    pass


class PNCPValidationError(PNCPClientError):
    pass


@dataclass
class ProbeResult:
    ok: bool
    status_code: int | None
    elapsed_seconds: float | None
    message: str


class PNCPClient:
    def __init__(self, base_url: str = PNCP_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.timeout = (PNCP_CONNECT_TIMEOUT, PNCP_READ_TIMEOUT)
        self.session = requests.Session()
        self.session.headers.update({'accept': '*/*', 'User-Agent': REQUESTS_USER_AGENT})
        retry = Retry(
            total=PNCP_MAX_RETRIES,
            connect=PNCP_MAX_RETRIES,
            read=PNCP_MAX_RETRIES,
            status=PNCP_MAX_RETRIES,
            backoff_factor=PNCP_RETRY_BACKOFF,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
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

    def _get(self, path: str, params: dict[str, Any]) -> dict[str, Any] | list[Any]:
        url = f'{self.base_url}{path}'
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise PNCPClientError(str(exc)) from exc

        if response.status_code == 204:
            return {'data': [], 'empty': True, 'totalPaginas': 0, 'numeroPagina': params.get('pagina', 1)}
        if response.status_code == 400:
            message = self._parse_error_message(response)
            if 'codigoModalidadeContratacao' in message:
                raise PNCPValidationError(message)
            raise PNCPClientError(message)
        if response.status_code >= 400:
            raise PNCPClientError(self._parse_error_message(response))
        try:
            return response.json()
        except ValueError as exc:
            raise PNCPClientError(f'Resposta JSON inválida do PNCP: {exc}') from exc

    def probe(self, codigo_modalidade: int | None = None) -> ProbeResult:
        start = time.perf_counter()
        params: dict[str, Any] = {'dataFinal': time.strftime('%Y-%m-%d'), 'pagina': 1, 'tamanhoPagina': 1}
        if codigo_modalidade:
            params['codigoModalidadeContratacao'] = codigo_modalidade
        try:
            payload = self._get('/v1/contratacoes/proposta', params)
            elapsed = round(time.perf_counter() - start, 2)
            total = payload.get('totalRegistros') if isinstance(payload, dict) else None
            return ProbeResult(True, 200, elapsed, f'Conexão OK. totalRegistros={total}')
        except Exception as exc:
            elapsed = round(time.perf_counter() - start, 2)
            return ProbeResult(False, None, elapsed, str(exc))

    def list_open_opportunities(
        self,
        *,
        data_final: str,
        pagina: int,
        tamanho_pagina: int,
        codigo_modalidade: int | None = None,
        uf: str | None = None,
        codigo_municipio_ibge: str | None = None,
        cnpj: str | None = None,
        codigo_unidade_administrativa: str | None = None,
        id_usuario: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            'dataFinal': data_final,
            'pagina': pagina,
            'tamanhoPagina': tamanho_pagina,
        }
        if codigo_modalidade is not None:
            params['codigoModalidadeContratacao'] = codigo_modalidade
        if uf:
            params['uf'] = uf
        if codigo_municipio_ibge:
            params['codigoMunicipioIbge'] = codigo_municipio_ibge
        if cnpj:
            params['cnpj'] = cnpj
        if codigo_unidade_administrativa:
            params['codigoUnidadeAdministrativa'] = codigo_unidade_administrativa
        if id_usuario:
            params['idUsuario'] = id_usuario
        payload = self._get('/v1/contratacoes/proposta', params)
        return payload if isinstance(payload, dict) else {'data': payload, 'empty': not payload, 'totalPaginas': 1, 'numeroPagina': pagina}

    def get_opportunity_detail(self, *, cnpj: str, ano: int, sequencial: int) -> dict[str, Any]:
        payload = self._get(f'/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}', {})
        if not isinstance(payload, dict):
            raise PNCPClientError('Detalhe da contratação retornou formato inválido.')
        return payload
