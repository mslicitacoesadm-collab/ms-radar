from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app.core.config import (
    PNCP_CONNECT_TIMEOUT,
    PNCP_MAX_RETRIES,
    PNCP_PORTAL_BASE_URL,
    PNCP_READ_TIMEOUT,
    PNCP_RETRY_BACKOFF,
    REQUESTS_USER_AGENT,
)


class PNCPScraperError(Exception):
    pass


@dataclass
class ScraperProbe:
    ok: bool
    message: str
    elapsed_seconds: float | None = None


class PNCPScraper:
    def __init__(self, base_url: str = PNCP_PORTAL_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.timeout = (PNCP_CONNECT_TIMEOUT, PNCP_READ_TIMEOUT)
        self.session = requests.Session()
        self.session.headers.update(
            {
                'User-Agent': REQUESTS_USER_AGENT,
                'Accept': 'text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8',
                'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.7',
                'Referer': f'{self.base_url}/app/editais',
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
        adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def _get_text(self, path: str, params: dict[str, Any] | None = None) -> str:
        url = f'{self.base_url}{path}'
        try:
            resp = self.session.get(url, params=params or {}, timeout=self.timeout)
            resp.raise_for_status()
            return resp.text
        except requests.RequestException as exc:
            raise PNCPScraperError(str(exc)) from exc

    def probe(self) -> ScraperProbe:
        import time

        start = time.perf_counter()
        try:
            html = self._get_text('/app/editais', {'pagina': 1, 'q': '', 'status': 'recebendo_proposta'})
            elapsed = round(time.perf_counter() - start, 2)
            if 'Portal Nacional de Contratações Públicas' in html or '/app/editais' in html:
                return ScraperProbe(True, 'Portal acessível via scraping.', elapsed)
            return ScraperProbe(False, 'HTML recebido sem marcadores esperados do portal.', elapsed)
        except Exception as exc:
            elapsed = round(time.perf_counter() - start, 2)
            return ScraperProbe(False, str(exc), elapsed)

    def list_open_opportunities(self, *, pagina: int = 1, query: str = '') -> dict[str, Any]:
        html = self._get_text('/app/editais', {'pagina': pagina, 'q': query, 'status': 'recebendo_proposta'})
        items = self._extract_items_from_html(html)
        return {
            'data': items,
            'numeroPagina': pagina,
            'totalPaginas': pagina if not items else pagina + 1,
            'empty': not items,
        }

    def get_opportunity_detail(self, cnpj: str, ano: int, sequencial: int) -> dict[str, Any]:
        html = self._get_text(f'/app/editais/{cnpj}/{ano}/{str(sequencial).zfill(6)}')
        for obj in self._yield_json_objects(html):
            if isinstance(obj, dict) and (obj.get('numeroControlePNCP') or obj.get('anoCompra')):
                return obj
        return {
            'linkSistemaOrigem': f'{self.base_url}/app/editais/{cnpj}/{ano}/{str(sequencial).zfill(6)}',
            'linkProcessoEletronico': '',
        }

    def _yield_json_objects(self, html: str) -> Iterable[Any]:
        soup = BeautifulSoup(html, 'lxml')
        for script in soup.find_all('script'):
            text = script.get_text(' ', strip=True)
            if not text:
                continue
            candidates: list[str] = []
            if script.get('id') == '__NEXT_DATA__':
                candidates.append(text)
            candidates.extend(re.findall(r'\{.*?numeroControlePNCP.*?\}', text, flags=re.DOTALL))
            candidates.extend(re.findall(r'\{.*?anoCompra.*?sequencialCompra.*?\}', text, flags=re.DOTALL))
            for candidate in candidates:
                try:
                    yield json.loads(candidate)
                except Exception:
                    for inner in re.findall(r'(\{[^{}]{50,}\})', candidate, flags=re.DOTALL):
                        try:
                            yield json.loads(inner)
                        except Exception:
                            pass

    def _extract_items_from_html(self, html: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        seen: set[str] = set()
        for obj in self._yield_json_objects(html):
            self._collect_items(obj, items, seen)
        if items:
            return items
        for match in re.finditer(r'/app/editais/(\d{14})/(\d{4})/(\d{6})', html):
            cnpj, ano, seq = match.groups()
            control = f'{cnpj}-1-{seq}/{ano}'
            if control in seen:
                continue
            seen.add(control)
            items.append(
                {
                    'numeroControlePNCP': control,
                    'anoCompra': int(ano),
                    'sequencialCompra': int(seq),
                    'objetoCompra': '',
                    'numeroCompra': seq,
                    'orgaoEntidade': {'cnpj': cnpj, 'razaoSocial': ''},
                    'unidadeOrgao': {'municipioNome': '', 'ufSigla': ''},
                    'linkSistemaOrigem': f'{self.base_url}/app/editais/{cnpj}/{ano}/{seq}',
                }
            )
        return items

    def _collect_items(self, obj: Any, items: list[dict[str, Any]], seen: set[str]) -> None:
        if isinstance(obj, dict):
            if ('numeroControlePNCP' in obj or 'numeroControlePncp' in obj) and ('anoCompra' in obj or 'sequencialCompra' in obj):
                control = obj.get('numeroControlePNCP') or obj.get('numeroControlePncp')
                if control and control not in seen:
                    seen.add(control)
                    items.append(obj)
            for value in obj.values():
                self._collect_items(value, items, seen)
        elif isinstance(obj, list):
            for value in obj:
                self._collect_items(value, items, seen)
