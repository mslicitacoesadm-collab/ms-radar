from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import requests

from .config import SAMPLE_JSON_PATH, load_settings

BASE_URL = "https://pncp.gov.br/api/consulta"
PROPOSTA_ENDPOINT = "/v1/contratacoes/proposta"
COMPRA_ENDPOINT = "/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}"

MODALITY_MAP = {
    1: "Leilão - Eletrônico",
    2: "Diálogo Competitivo",
    3: "Concurso",
    4: "Concorrência - Eletrônica",
    5: "Concorrência - Presencial",
    6: "Pregão - Eletrônico",
    7: "Pregão - Presencial",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
    10: "Manifestação de Interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão - Presencial",
}


class PNCPClient:
    def __init__(self) -> None:
        self.settings = load_settings()
        self.timeout = self.settings.pncp_timeout
        self.base_url = self.settings.pncp_search_url.strip() or BASE_URL
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json", "User-Agent": "radar-licitacoes/2.0"})

    def search(self, query: str = "", days: int = 30, page: int = 1, page_size: int = 50, limit_pages: int = 3) -> List[Dict]:
        try:
            rows = self.fetch_open_proposals(days=days, start_page=page, page_size=page_size, limit_pages=limit_pages)
            if rows:
                return self._filter_client_side(rows, query)
        except Exception:
            pass
        return self.load_sample()

    def fetch_open_proposals(
        self,
        days: int = 30,
        start_page: int = 1,
        page_size: int = 50,
        limit_pages: int = 3,
        uf: str = "",
        codigo_municipio_ibge: str = "",
        codigo_modalidade: Optional[int] = None,
    ) -> List[Dict]:
        end_date = (date.today() + timedelta(days=max(days, 1))).isoformat()
        normalized: List[Dict] = []

        for page in range(start_page, start_page + max(limit_pages, 1)):
            payload = self._fetch_proposals_page(
                end_date=end_date,
                page=page,
                page_size=page_size,
                uf=uf,
                codigo_municipio_ibge=codigo_municipio_ibge,
                codigo_modalidade=codigo_modalidade,
            )
            parsed = self._parse_payload(payload)
            if not parsed:
                break
            normalized.extend(parsed)

            total_pages = int(payload.get("totalPaginas") or 0) if isinstance(payload, dict) else 0
            current_page = int(payload.get("numeroPagina") or page) if isinstance(payload, dict) else page
            if total_pages and current_page >= total_pages:
                break

        return self._deduplicate(normalized)

    def import_json_file(self, payload: bytes) -> List[Dict]:
        data = json.loads(payload.decode("utf-8"))
        return self._parse_payload(data)

    def load_sample(self) -> List[Dict]:
        data = json.loads(Path(SAMPLE_JSON_PATH).read_text(encoding="utf-8"))
        return self._parse_payload(data)

    def _fetch_proposals_page(
        self,
        end_date: str,
        page: int,
        page_size: int,
        uf: str = "",
        codigo_municipio_ibge: str = "",
        codigo_modalidade: Optional[int] = None,
    ) -> Dict:
        params = {
            "dataFinal": end_date,
            "pagina": page,
            "tamanhoPagina": page_size,
        }
        if uf:
            params["uf"] = uf.upper()
        if codigo_municipio_ibge:
            params["codigoMunicipioIbge"] = codigo_municipio_ibge
        if codigo_modalidade is not None:
            params["codigoModalidadeContratacao"] = int(codigo_modalidade)

        response = self.session.get(f"{self.base_url.rstrip('/')}{PROPOSTA_ENDPOINT}", params=params, timeout=self.timeout)
        if response.status_code == 204:
            return {"data": [], "totalPaginas": 0, "numeroPagina": page}
        response.raise_for_status()
        return response.json()

    def _fetch_purchase_detail(self, cnpj: str, ano: int, sequencial: int) -> Dict:
        endpoint = COMPRA_ENDPOINT.format(cnpj=cnpj, ano=ano, sequencial=sequencial)
        response = self.session.get(f"{self.base_url.rstrip('/')}{endpoint}", timeout=self.timeout)
        if response.status_code == 204:
            return {}
        response.raise_for_status()
        return response.json()

    def _parse_payload(self, data: object) -> List[Dict]:
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("items") or data.get("data") or data.get("resultados") or data.get("content") or []
        else:
            items = []

        normalized: List[Dict] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            cnpj = self._get_nested(item, "orgaoEntidade.cnpj") or item.get("cnpj") or ""
            ano = self._get_nested(item, "anoCompra") or item.get("ano") or ""
            sequencial = self._get_nested(item, "sequencialCompra") or item.get("sequencial") or ""
            modality_code = self._get_nested(item, "modalidadeId") or self._get_nested(item, "codigoModalidadeContratacao") or item.get("modalidade")

            normalized.append(
                {
                    "source_id": self._first(item, "numeroControlePNCP", "source_id", "id", "numeroCompra", "sequencialCompra") or f"item-{len(normalized)+1}",
                    "title": self._build_title(item),
                    "object_text": self._first(item, "object_text", "objetoCompra", "objeto", "descricao", "informacaoComplementar") or "",
                    "agency": self._first(item, "agency", "orgaoEntidade.razaoSocial", "orgaoEntidade.nome", "nomeOrgaoEntidade", "unidadeOrgao.nomeUnidade") or "Órgão não informado",
                    "state": self._first(item, "state", "unidadeOrgao.ufSigla", "uf", "siglaUf") or "",
                    "city": self._first(item, "city", "unidadeOrgao.municipioNome", "municipioNome", "cidade", "nomeMunicipio") or "",
                    "modality": self._first(item, "modality", "modalidadeNome", "modalidade", "modoDisputaNome") or MODALITY_MAP.get(self._safe_int(modality_code), ""),
                    "estimated_value": self._to_float(self._first(item, "estimated_value", "valorTotalEstimado", "valorEstimado", "valorTotalHomologado")),
                    "publication_date": self._first(item, "publication_date", "dataPublicacaoPncp", "dataPublicacao", "dataInclusao") or "",
                    "deadline_date": self._first(item, "deadline_date", "dataEncerramentoProposta", "dataAberturaProposta", "dataFimRecebimentoPropostas", "data") or "",
                    "source_url": self._first(item, "source_url", "linkSistemaOrigem", "url", "link", "linkProcessoEletronico", "linkProcesso") or self._build_detail_url(cnpj, ano, sequencial),
                    "source_system": self._first(item, "source_system", "sistemaOrigem") or "PNCP",
                    "pncp_cnpj": str(cnpj),
                    "pncp_ano": self._safe_int(ano),
                    "pncp_sequencial": self._safe_int(sequencial),
                }
            )
        return normalized

    def _filter_client_side(self, rows: List[Dict], query: str) -> List[Dict]:
        q = (query or "").strip().lower()
        if not q:
            return rows
        out: List[Dict] = []
        for row in rows:
            bag = " ".join(
                [
                    str(row.get("title", "")),
                    str(row.get("object_text", "")),
                    str(row.get("agency", "")),
                    str(row.get("city", "")),
                    str(row.get("state", "")),
                    str(row.get("modality", "")),
                ]
            ).lower()
            if q in bag:
                out.append(row)
        return out or rows

    def fetch_and_enrich_notice(self, notice: Dict) -> Dict:
        cnpj = str(notice.get("pncp_cnpj") or "")
        ano = self._safe_int(notice.get("pncp_ano"))
        sequencial = self._safe_int(notice.get("pncp_sequencial"))
        if not (cnpj and ano and sequencial):
            return notice
        try:
            detail = self._fetch_purchase_detail(cnpj, ano, sequencial)
        except Exception:
            return notice
        if not isinstance(detail, dict) or not detail:
            return notice

        merged = dict(notice)
        merged["object_text"] = self._first(detail, "objetoCompra", "informacaoComplementar") or merged.get("object_text", "")
        merged["source_url"] = self._first(detail, "linkSistemaOrigem", "linkProcessoEletronico") or merged.get("source_url", "")
        merged["estimated_value"] = self._to_float(self._first(detail, "valorTotalEstimado", "valorTotalHomologado") or merged.get("estimated_value"))
        merged["agency"] = self._first(detail, "orgaoEntidade.razaoSocial", "unidadeOrgao.nomeUnidade") or merged.get("agency", "")
        merged["city"] = self._first(detail, "unidadeOrgao.municipioNome") or merged.get("city", "")
        merged["state"] = self._first(detail, "unidadeOrgao.ufSigla") or merged.get("state", "")
        return merged

    def _build_title(self, item: Dict) -> str:
        number = self._first(item, "numeroCompra") or "Sem número"
        modality = self._first(item, "modalidadeNome", "modalidade") or MODALITY_MAP.get(self._safe_int(self._get_nested(item, "modalidadeId") or item.get("codigoModalidadeContratacao")), "Licitação")
        obj = self._first(item, "objetoCompra", "objeto", "descricao") or "Objeto não informado"
        return f"{modality} {number} — {obj}"[:300]

    def _build_detail_url(self, cnpj: object, ano: object, sequencial: object) -> str:
        if not (cnpj and ano and sequencial):
            return ""
        return f"{self.base_url.rstrip('/')}{COMPRA_ENDPOINT.format(cnpj=cnpj, ano=ano, sequencial=sequencial)}"

    def _deduplicate(self, rows: List[Dict]) -> List[Dict]:
        seen = set()
        out: List[Dict] = []
        for row in rows:
            key = str(row.get("source_id") or "")
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(row)
        return out

    def _first(self, item: Dict, *keys: str) -> Optional[str]:
        for key in keys:
            value = self._get_nested(item, key)
            if value not in (None, ""):
                return str(value)
        return None

    def _get_nested(self, item: Dict, key: str):
        parts = key.split(".")
        current = item
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _safe_int(self, value: object) -> int:
        try:
            return int(str(value))
        except Exception:
            return 0

    def _to_float(self, value: object) -> float:
        if value in (None, ""):
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).replace("R$", "").strip()
        if "," in text and "." in text:
            text = text.replace(".", "").replace(",", ".")
        elif "," in text:
            text = text.replace(",", ".")
        try:
            return float(text)
        except ValueError:
            return 0.0
