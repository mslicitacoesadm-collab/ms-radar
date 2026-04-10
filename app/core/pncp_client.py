from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import time
from typing import Any

import requests

from app.core.config import DEFAULT_TIMEOUT, PNCP_BASE_URL, REQUESTS_USER_AGENT


class PNCPClientError(Exception):
    pass


@dataclass
class WindowResult:
    seen: int
    inserted: int
    updated: int
    pages: int


class PNCPClient:
    def __init__(self, base_url: str = PNCP_BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({'accept': '*/*', 'User-Agent': REQUESTS_USER_AGENT})

    def _get(self, path: str, params: dict[str, Any], retries: int = 3) -> dict[str, Any] | list[Any]:
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                response = self.session.get(f'{self.base_url}{path}', params=params, timeout=self.timeout)
                if response.status_code == 204:
                    return {'data': [], 'empty': True, 'totalPaginas': 0, 'numeroPagina': params.get('pagina', 1)}
                response.raise_for_status()
                return response.json()
            except requests.RequestException as exc:
                last_error = exc
                if attempt == retries:
                    break
                time.sleep(1.5 * attempt)
        raise PNCPClientError(str(last_error))

    def list_open_opportunities(
        self,
        *,
        data_final: str,
        pagina: int,
        tamanho_pagina: int = 50,
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
        if codigo_modalidade:
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
        return self._get('/v1/contratacoes/proposta', params)

    def list_publications(
        self,
        *,
        data_inicial: str,
        data_final: str,
        codigo_modalidade: int,
        pagina: int,
        tamanho_pagina: int = 50,
        codigo_modo_disputa: int | None = None,
        uf: str | None = None,
        codigo_municipio_ibge: str | None = None,
        cnpj: str | None = None,
        codigo_unidade_administrativa: str | None = None,
        id_usuario: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            'dataInicial': data_inicial,
            'dataFinal': data_final,
            'codigoModalidadeContratacao': codigo_modalidade,
            'pagina': pagina,
            'tamanhoPagina': tamanho_pagina,
        }
        if codigo_modo_disputa:
            params['codigoModoDisputa'] = codigo_modo_disputa
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
        return self._get('/v1/contratacoes/publicacao', params)

    def get_opportunity_detail(self, *, cnpj: str, ano: int, sequencial: int) -> dict[str, Any]:
        return self._get(f'/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}', {})

    def sync_open_windows(self, days_back: int = 3) -> list[dict[str, str]]:
        today = date.today()
        return [{'data_final': (today + timedelta(days=offset)).isoformat()} for offset in range(0, days_back + 1)]
