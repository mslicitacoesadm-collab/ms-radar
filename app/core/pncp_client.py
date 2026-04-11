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
    PNCP_SOURCE_MODE,
    REQUESTS_USER_AGENT,
)
from app.core.pncp_scraper import PNCPScraper, PNCPScraperError


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
    source: str = 'api'


class PNCPClient:
    def __init__(self, base_url: str = PNCP_BASE_URL, source_mode: str = PNCP_SOURCE_MODE):
        self.base_url = base_url.rstrip('/')
        self.source_mode = source_mode
        self.timeout = (PNCP_CONNECT_TIMEOUT, PNCP_READ_TIMEOUT)
        self.session = requests.Session()
        self.session.headers.update(
            {
                'accept': '*/*',
                'User-Agent': REQUESTS_USER_AGENT,
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.7',
                'Referer': 'https://pncp.gov.br/',
                'Cache-Control': 'no-cache',
            }
        )
        retry = Retry(
            total=PNCP_MAX_RETRIES,
            connect=PNCP_MAX_RETRIES,
            read=PNCP_MAX_RETRIES,
            status=PNCP_MAX_RETRIES,
            backoff_factor=PNCP_RETRY_BACKOFF,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=['GET'],
            raise_on_status=False,
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        self.scraper = PNCPScraper()

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
        params: dict[str, Any] = {'dataFinal': time.strftime('%Y-%m-%d'), 'pagina': 1, 'tamanhoPagina': 10}
        if codigo_modalidade:
            params['codigoModalidadeContratacao'] = codigo_modalidade

        if self.source_mode in ('api', 'hybrid'):
            try:
                payload = self._get('/v1/contratacoes/proposta', params)
                elapsed = round(time.perf_counter() - start, 2)
                total = payload.get('totalRegistros') if isinstance(payload, dict) else None
                return ProbeResult(True, 200, elapsed, f'Conexão API OK. totalRegistros={total}', 'api')
            except Exception as exc:
                if self.source_mode == 'api':
                    elapsed = round(time.perf_counter() - start, 2)
                    return ProbeResult(False, None, elapsed, str(exc), 'api')
        try:
            sc = self.scraper.probe()
            return ProbeResult(sc.ok, 200 if sc.ok else None, sc.elapsed_seconds, sc.message, 'scraping')
        except Exception as exc:
            elapsed = round(time.perf_counter() - start, 2)
            return ProbeResult(False, None, elapsed, str(exc), 'scraping')

    def list_open_opportunities(
        self,
        *,
        data_final: str,
        pagina: int,
        tamanho_pagina: int,
        codigo_modalidade: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        tamanho_pagina = max(10, int(tamanho_pagina))
        last_error = None
        if self.source_mode in ('api', 'hybrid'):
            params: dict[str, Any] = {'dataFinal': data_final, 'pagina': pagina, 'tamanhoPagina': tamanho_pagina}
            if codigo_modalidade is not None:
                params['codigoModalidadeContratacao'] = codigo_modalidade
            for key in ('uf', 'codigo_municipio_ibge', 'cnpj', 'codigo_unidade_administrativa', 'id_usuario'):
                val = kwargs.get(key)
                if val is not None:
                    map_key = {
                        'codigo_municipio_ibge': 'codigoMunicipioIbge',
                        'codigo_unidade_administrativa': 'codigoUnidadeAdministrativa',
                        'id_usuario': 'idUsuario',
                    }.get(key, key)
                    params[map_key] = val
            try:
                payload = self._get('/v1/contratacoes/proposta', params)
                result = payload if isinstance(payload, dict) else {'data': payload, 'empty': not payload, 'totalPaginas': 1, 'numeroPagina': pagina}
                result['_source'] = 'api'
                return result
            except Exception as exc:
                last_error = exc
                if self.source_mode == 'api':
                    raise
        if self.source_mode in ('scraping', 'hybrid'):
            try:
                result = self.scraper.list_open_opportunities(pagina=pagina)
                result['_source'] = 'scraping'
                return result
            except Exception as exc:
                if last_error:
                    raise PNCPClientError(f'API: {last_error} | Scraping: {exc}') from exc
                raise PNCPClientError(str(exc)) from exc
        if last_error:
            raise PNCPClientError(str(last_error))
        raise PNCPClientError('Nenhuma fonte PNCP habilitada.')

    def get_opportunity_detail(self, *, cnpj: str, ano: int, sequencial: int) -> dict[str, Any]:
        last_error = None
        if self.source_mode in ('api', 'hybrid'):
            try:
                payload = self._get(f'/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}', {})
                if not isinstance(payload, dict):
                    raise PNCPClientError('Detalhe da contratação retornou formato inválido.')
                payload['_source'] = 'api'
                return payload
            except Exception as exc:
                last_error = exc
                if self.source_mode == 'api':
                    raise
        if self.source_mode in ('scraping', 'hybrid'):
            try:
                payload = self.scraper.get_opportunity_detail(cnpj, ano, sequencial)
                payload['_source'] = 'scraping'
                return payload
            except (PNCPClientError, PNCPScraperError) as exc:
                if last_error:
                    raise PNCPClientError(f'API: {last_error} | Scraping: {exc}') from exc
                raise PNCPClientError(str(exc)) from exc
        if last_error:
            raise PNCPClientError(str(last_error))
        raise PNCPClientError('Nenhuma fonte PNCP habilitada.')
