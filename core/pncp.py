from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Iterable
import os
import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PNCP_BASE = os.getenv("PNCP_BASE", "https://pncp.gov.br/api/consulta")
USER_AGENT = os.getenv("MS_RADAR_USER_AGENT", "MS Radar/10.1 (+https://mslicitacoes.com)")

MODALIDADES: dict[int, str] = {
    1: "Concorrência",
    2: "Tomada de Preços",
    3: "Convite",
    4: "Concorrência Eletrônica",
    5: "Leilão",
    6: "Pregão Eletrônico",
    7: "Concurso",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
    10: "Manifestação de Interesse",
    11: "Pré-qualificação",
    12: "Credenciamento",
    13: "Leilão Eletrônico",
}

HOME_MODALIDADES = [6, 8, 4]


@dataclass
class PNCPResult:
    notices: list[dict[str, Any]]
    source: str
    ok: bool
    message: str
    elapsed_ms: int = 0


class PNCPClientError(Exception):
    pass


def compact_date(d: date | datetime | str | None = None) -> str:
    """PNCP consulta costuma aceitar datas no padrão AAAAMMDD."""
    if d is None:
        d = date.today()
    if isinstance(d, datetime):
        d = d.date()
    if isinstance(d, date):
        return d.strftime("%Y%m%d")
    raw = str(d).strip()
    digits = re.sub(r"\D", "", raw)
    if len(digits) >= 8:
        # aceita YYYYMMDD ou DDMMYYYY; se começa com 20, assume YYYYMMDD
        if digits[:2] == "20":
            return digits[:8]
        return digits[4:8] + digits[2:4] + digits[0:2]
    return date.today().strftime("%Y%m%d")


def iso_date(value: Any) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    raw = str(value).strip()
    if not raw:
        return None
    if "T" in raw:
        raw = raw.split("T", 1)[0]
    digits = re.sub(r"\D", "", raw)
    candidates = []
    if len(digits) >= 8:
        if digits[:2] == "20":
            candidates.append((digits[:4], digits[4:6], digits[6:8]))
        candidates.append((digits[4:8], digits[2:4], digits[0:2]))
    for y, m, d in candidates:
        try:
            return date(int(y), int(m), int(d)).isoformat()
        except Exception:
            pass
    return raw[:10]


def to_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace("R$", "").replace(" ", "")
    # 1.234,56 -> 1234.56
    if "," in text and "." in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except Exception:
        return None


def first_text(*values: Any) -> str:
    for v in values:
        if v not in (None, ""):
            txt = str(v).strip()
            if txt:
                return txt
    return ""


def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=1,
        connect=1,
        read=1,
        status=1,
        backoff_factor=0.2,
        status_forcelist=(408, 429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=12, pool_maxsize=12)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    s.headers.update({
        "Accept": "application/json, text/plain, */*",
        "User-Agent": USER_AGENT,
        "Accept-Language": "pt-BR,pt;q=0.9",
    })
    return s


def extract_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("data", "content", "items", "resultado", "resultados"):
        value = payload.get(key)
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
    # alguns retornos vêm como {"data": {"content": [...]}}
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("content", "items", "resultados"):
            value = data.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def pncp_public_url(numero_controle: str | None) -> str:
    if not numero_controle:
        return "https://pncp.gov.br/app/editais"
    return f"https://pncp.gov.br/app/editais/{numero_controle}"


def normalize(item: dict[str, Any]) -> dict[str, Any]:
    orgao = item.get("orgaoEntidade") or {}
    unidade = item.get("unidadeOrgao") or {}
    mod_code = item.get("codigoModalidadeContratacao") or item.get("modalidadeId")
    try:
        mod_code_int = int(mod_code) if mod_code not in (None, "") else None
    except Exception:
        mod_code_int = None

    numero_controle = first_text(item.get("numeroControlePNCP"), item.get("numeroControlePncp"))
    modalidade = first_text(item.get("modalidadeNome"), item.get("nomeModalidade"), MODALIDADES.get(mod_code_int), item.get("modalidade"))
    objeto = first_text(item.get("objetoCompra"), item.get("objeto"), item.get("descricao"), item.get("informacaoComplementar"))
    title = objeto or first_text(item.get("titulo"), f"{modalidade} {item.get('numeroCompra','')}")
    uf = first_text(item.get("ufSigla"), item.get("uf"), unidade.get("ufSigla"), unidade.get("uf"))
    cidade = first_text(item.get("municipioNome"), item.get("nomeMunicipioIbge"), unidade.get("municipioNome"), unidade.get("nomeMunicipioIbge"))
    orgao_nome = first_text(orgao.get("razaoSocial"), orgao.get("nome"), item.get("orgaoEntidadeRazaoSocial"), unidade.get("nomeUnidade"), item.get("unidadeOrgaoNomeUnidade"))
    valor = to_float(first_text(item.get("valorTotalEstimado"), item.get("valorEstimado"), item.get("valorGlobal"), item.get("valorTotalHomologado")))
    link_origem = first_text(item.get("linkSistemaOrigem"), item.get("urlSistemaOrigem"), item.get("linkProcessoEletronico"))
    return {
        "id": numero_controle or first_text(item.get("id"), item.get("numeroCompra"), title),
        "numero_controle_pncp": numero_controle,
        "title": title[:500],
        "object_text": objeto[:1200],
        "agency": orgao_nome,
        "state": uf.upper()[:2] if uf else "",
        "city": cidade,
        "modality": modalidade,
        "modality_code": mod_code_int,
        "estimated_value": valor,
        "publication_date": iso_date(first_text(item.get("dataPublicacaoPncp"), item.get("dataPublicacao"), item.get("dataInclusao"))),
        "deadline_date": iso_date(first_text(item.get("dataEncerramentoProposta"), item.get("dataFimRecebimentoProposta"), item.get("dataEncerramento"))),
        "opening_date": iso_date(first_text(item.get("dataAberturaProposta"), item.get("dataInicioRecebimentoProposta"), item.get("dataAbertura"))),
        "situation": first_text(item.get("situacaoCompraNome"), item.get("situacaoNome"), item.get("situacaoCompraId")),
        "source_url": link_origem or pncp_public_url(numero_controle),
        "raw": item,
    }


def fetch_endpoint(endpoint: str, *, modalidade: int | None = None, uf: str = "", page: int = 1, page_size: int = 10, timeout: float = 6.0, start_days: int = 30) -> list[dict[str, Any]]:
    session = make_session()
    today = date.today()
    params: dict[str, Any] = {
        "pagina": page,
        "tamanhoPagina": page_size,
    }
    if endpoint == "publicacao":
        params["dataInicial"] = compact_date(today - timedelta(days=start_days))
        params["dataFinal"] = compact_date(today)
    else:
        # propostas abertas: data final da proposta até hoje/futuro conforme endpoint do PNCP
        params["dataFinal"] = compact_date(today + timedelta(days=60))
    if modalidade:
        params["codigoModalidadeContratacao"] = modalidade
    if uf:
        params["uf"] = uf.upper()

    url = f"{PNCP_BASE}/v1/contratacoes/{endpoint}"
    response = session.get(url, params=params, timeout=(2.5, timeout))
    if response.status_code >= 400:
        raise PNCPClientError(f"PNCP HTTP {response.status_code}: {response.text[:180]}")
    try:
        payload = response.json()
    except Exception as exc:
        raise PNCPClientError(f"Resposta não JSON do PNCP: {exc}") from exc
    return [normalize(x) for x in extract_list(payload)]


def dedupe(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in items:
        key = item.get("numero_controle_pncp") or item.get("id") or f"{item.get('title')}|{item.get('agency')}|{item.get('deadline_date')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def sort_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def k(x: dict[str, Any]):
        prazo = x.get("deadline_date") or "9999-12-31"
        valor = x.get("estimated_value") or 0
        return (prazo, -valor)
    return sorted(items, key=k)


def live_home_feed(limit: int = 12, uf: str = "", timeout: float = 5.0) -> PNCPResult:
    """Feed inicial rápido: poucas chamadas paralelas. Não faz varredura pesada."""
    started = datetime.now()
    errors: list[str] = []
    items: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(fetch_endpoint, "proposta", modalidade=m, uf=uf, page=1, page_size=8, timeout=timeout) for m in HOME_MODALIDADES]
        for fut in as_completed(futures):
            try:
                items.extend(fut.result())
            except Exception as exc:
                errors.append(str(exc))
    items = sort_items(dedupe(items))[:limit]
    elapsed = int((datetime.now() - started).total_seconds() * 1000)
    if items:
        return PNCPResult(items, "PNCP ao vivo", True, f"{len(items)} oportunidades carregadas do PNCP.", elapsed)

    # fallback controlado: tenta publicações recentes, que costuma ser mais tolerante
    try:
        pub = fetch_endpoint("publicacao", modalidade=6, uf=uf, page=1, page_size=limit, timeout=timeout, start_days=15)
        pub = sort_items(dedupe(pub))[:limit]
        if pub:
            return PNCPResult(pub, "PNCP publicações", True, f"Carregadas {len(pub)} publicações recentes do PNCP.", elapsed)
    except Exception as exc:
        errors.append(str(exc))

    return PNCPResult([], "indisponível", False, "Não foi possível carregar dados do PNCP agora. Verifique conexão/endpoint ou tente novamente.", elapsed)


def advanced_search(*, query: str = "", uf: str = "", modalidade: int | None = None, endpoint: str = "proposta", pages: int = 1, page_size: int = 20) -> PNCPResult:
    started = datetime.now()
    items: list[dict[str, Any]] = []
    errors: list[str] = []
    mods = [modalidade] if modalidade else HOME_MODALIDADES
    jobs = []
    with ThreadPoolExecutor(max_workers=min(6, len(mods) * max(1, pages))) as ex:
        for m in mods:
            for p in range(1, max(1, pages) + 1):
                jobs.append(ex.submit(fetch_endpoint, endpoint, modalidade=m, uf=uf, page=p, page_size=page_size, timeout=8.0))
        for fut in as_completed(jobs):
            try:
                items.extend(fut.result())
            except Exception as exc:
                errors.append(str(exc))
    items = sort_items(dedupe(items))
    if query:
        items = filter_items(items, query=query)
    elapsed = int((datetime.now() - started).total_seconds() * 1000)
    if items:
        return PNCPResult(items, "PNCP ao vivo", True, f"{len(items)} resultados encontrados.", elapsed)
    return PNCPResult([], "PNCP", False, "Nenhum resultado retornado para esses filtros." + (f" Erros: {errors[:1]}" if errors else ""), elapsed)


def filter_items(items: list[dict[str, Any]], *, query: str = "", uf: str = "", city: str = "", modality: str = "") -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    out = []
    for it in items:
        if uf and it.get("state") != uf:
            continue
        if city and city.lower() not in (it.get("city") or "").lower():
            continue
        if modality and modality.lower() not in (it.get("modality") or "").lower():
            continue
        if q:
            hay = " ".join(str(it.get(k, "")) for k in ("title", "object_text", "agency", "city", "state", "modality")).lower()
            if q not in hay:
                continue
        out.append(it)
    return out


def days_to_deadline(item: dict[str, Any]) -> int | None:
    d = item.get("deadline_date")
    if not d:
        return None
    try:
        return (datetime.strptime(d[:10], "%Y-%m-%d").date() - date.today()).days
    except Exception:
        return None


def unique(items: list[dict[str, Any]], key: str) -> list[str]:
    return sorted({str(x.get(key)).strip() for x in items if x.get(key)})


def aggregate(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    counter: dict[str, int] = {}
    for x in items:
        val = str(x.get(key) or "Não informado").strip()
        counter[val] = counter.get(val, 0) + 1
    return [{key: k, "total": v} for k, v in sorted(counter.items(), key=lambda kv: kv[1], reverse=True)]
