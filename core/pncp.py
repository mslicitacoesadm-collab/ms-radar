from __future__ import annotations

import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests
import streamlit as st

API_BASE = "https://pncp.gov.br/api/consulta/v1"
DEFAULT_TIMEOUT = 7
MAX_WORKERS = 4
FAST_HOME_MODALIDADES = [6, 4, 8]
MAX_HOME_ITEMS = 12

MODALIDADES = {
    1: "Convite",
    2: "Tomada de Preços",
    3: "Concorrência",
    4: "Concorrência Eletrônica",
    5: "Concurso",
    6: "Pregão Eletrônico",
    7: "Pregão Presencial",
    8: "Dispensa de Licitação",
    9: "Inexigibilidade",
    10: "Leilão",
    11: "Diálogo Competitivo",
    12: "Manifestação de Interesse",
    13: "Pré-qualificação",
}

UFS = [
    "Todas", "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT",
    "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO",
]

NICHES = {
    "Limpeza e conservação": ["limpeza", "conservação", "higienização", "material de limpeza", "faxina"],
    "Medicamentos e saúde": ["medicamentos", "hospitalar", "saúde", "material hospitalar", "farmácia"],
    "Transporte e locação": ["transporte", "veículos", "locação", "combustível", "ônibus"],
    "Obras e engenharia": ["obra", "engenharia", "reforma", "construção", "pavimentação"],
    "Tecnologia e informática": ["software", "informática", "computadores", "licença", "sistema"],
    "Alimentação escolar": ["gêneros alimentícios", "merenda", "alimentação", "cestas", "alimentos"],
}

STATE_GROUPS = {
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
    "Centro-Oeste": ["DF", "GO", "MS", "MT"],
    "Norte": ["AC", "AM", "AP", "PA", "RO", "RR", "TO"],
}

CUSTOM_CSS = """
<style>
:root {
  --bg: #06111f;
  --panel: rgba(8, 19, 35, .92);
  --panel-2: rgba(11, 27, 50, .92);
  --line: rgba(116, 195, 255, .14);
  --text: #eef7ff;
  --muted: #9cb5cf;
  --blue1: #0b4fa8;
  --blue2: #33c8ff;
  --green: #22c55e;
  --amber: #f59e0b;
  --red: #ef4444;
}
html, body, .stApp {
  background:
    radial-gradient(circle at top left, rgba(51,200,255,.10), transparent 22%),
    radial-gradient(circle at top right, rgba(11,79,168,.18), transparent 23%),
    linear-gradient(180deg, #02070f 0%, #081321 100%);
  color: var(--text);
}
.block-container {max-width: 1420px; padding-top: 1rem; padding-bottom: 2rem;}
section[data-testid='stSidebar'], button[kind='header'], div[data-testid='collapsedControl'] {display:none !important;}
.hero, .surface, .kpi, .cta-box, .nav-box, .segment-box, .filter-shell {
  background: linear-gradient(180deg, rgba(8,19,35,.96), rgba(10,25,46,.92));
  border: 1px solid var(--line);
  border-radius: 24px;
  box-shadow: 0 18px 50px rgba(0,0,0,.28);
}
.hero {padding: 28px 30px;}
.hero h1 {font-size: 2.85rem; line-height: 1.02; margin: 10px 0 12px; color: white; letter-spacing: -0.02em;}
.hero p {font-size: 1rem; color: #d5e8fb; max-width: 980px;}
.hero-top {display:flex; align-items:center; gap:12px; flex-wrap:wrap;}
.ribbon {
  display:inline-flex; align-items:center; gap:8px; padding:8px 14px; border-radius:999px;
  background: rgba(51,200,255,.10); color:#e8f8ff; border:1px solid rgba(51,200,255,.22); font-weight:800; font-size:.83rem;
}
.kpi {padding: 18px; min-height: 128px;}
.kpi .label {color: var(--muted); font-size: .88rem;}
.kpi .value {font-size: 2rem; font-weight: 900; color: white; margin-top: 6px;}
.kpi .note {font-size: .85rem; color: #c4d7ea; margin-top: 8px;}
.section-title {font-size: 1.24rem; font-weight: 900; margin: 16px 0 12px; color: white;}
.section-sub {font-size: .92rem; color: var(--muted); margin-top: -4px; margin-bottom: 12px;}
.surface, .cta-box, .nav-box, .segment-box, .filter-shell {padding: 16px 18px;}
.card {
  border:1px solid var(--line); border-radius:24px; padding:18px; min-height:320px;
  background: linear-gradient(180deg, rgba(8,19,35,.96), rgba(7,16,31,.95)); box-shadow:0 10px 28px rgba(0,0,0,.22); margin-bottom: 14px;
}
.card h3 {margin:0; color:white; font-size:1rem; line-height:1.28;}
.card-orgao {color:#d4e5f6; margin-top:10px; font-weight:700; min-height:42px;}
.chips {display:flex; flex-wrap:wrap; gap:8px; margin:12px 0;}
.chip {padding:6px 10px; border-radius:999px; background:rgba(255,255,255,.05); border:1px solid rgba(255,255,255,.08); color:#dceeff; font-size:.77rem;}
.meta {display:grid; grid-template-columns:1fr 1fr; gap:10px; margin:10px 0 12px;}
.meta-box {padding:11px; border-radius:16px; background:rgba(255,255,255,.04); border:1px solid rgba(255,255,255,.06);}
.meta-label {font-size:.75rem; color:var(--muted);} .meta-value {font-size:.92rem; color:white; font-weight:900; margin-top:3px;}
.badge {padding:7px 10px; border-radius:999px; font-size:.74rem; font-weight:900; white-space:nowrap;}
.badge-ok {background: rgba(34,197,94,.12); color:#86efac; border:1px solid rgba(34,197,94,.24);} 
.badge-warn {background: rgba(245,158,11,.12); color:#fde68a; border:1px solid rgba(245,158,11,.24);} 
.badge-danger {background: rgba(239,68,68,.12); color:#fca5a5; border:1px solid rgba(239,68,68,.24);} 
.badge-neutral {background: rgba(148,163,184,.12); color:#cbd5e1; border:1px solid rgba(148,163,184,.24);} 
.actions {display:flex; justify-content:space-between; align-items:center; gap:10px; margin-top:14px;}
.btn-link {
  display:inline-flex; align-items:center; justify-content:center; text-decoration:none; font-weight:800; color:white !important;
  padding:10px 14px; border-radius:14px; background: linear-gradient(135deg, var(--blue1), var(--blue2));
}
.small, .muted {color: var(--muted);} 
.stDownloadButton button, .stButton button {
  border-radius: 14px !important; font-weight: 800 !important; min-height: 2.8rem;
}
.note-line {color:#bfe7ff; font-weight:700;}
</style>
"""


def setup_page(title: str = "MS Radar", icon: str = "📡") -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout="wide", initial_sidebar_state="collapsed")
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def money_br(value: Any) -> str:
    try:
        v = float(value)
        s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {s}"
    except Exception:
        return "Não informado"


def parse_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    raw = str(value).strip().replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw[:26], fmt)
        except Exception:
            continue
    return None


def date_br(value: Optional[str]) -> str:
    dt = parse_date(value)
    return dt.strftime("%d/%m/%Y %H:%M") if dt else "Não informado"


def days_left(value: Optional[str]) -> Optional[int]:
    dt = parse_date(value)
    if not dt:
        return None
    return math.floor((dt - datetime.now()).total_seconds() / 86400)


def urgency_label(value: Optional[str]) -> str:
    left = days_left(value)
    if left is None:
        return "Sem prazo"
    if left < 0:
        return "Encerrada"
    if left <= 1:
        return "Encerra hoje"
    if left <= 3:
        return "Prazo curto"
    return "Aberta"


def urgency_html(value: Optional[str]) -> str:
    label = urgency_label(value)
    css = {
        "Encerrada": "badge-danger",
        "Encerra hoje": "badge-danger",
        "Prazo curto": "badge-warn",
        "Aberta": "badge-ok",
        "Sem prazo": "badge-neutral",
    }.get(label, "badge-neutral")
    return f'<span class="badge {css}">{label}</span>'


def detect_niche(text: str) -> str:
    base = (text or "").lower()
    for niche, terms in NICHES.items():
        if any(term.lower() in base for term in terms):
            return niche
    return "Outros"


def score_item(item: Dict[str, Any], termo: str = "") -> float:
    score = 0.0
    prazo = item.get("dataEncerramentoProposta") or item.get("dataAberturaProposta")
    left = days_left(prazo)
    if left is not None:
        if 0 <= left <= 1:
            score += 45
        elif left <= 3:
            score += 28
        elif left <= 7:
            score += 16
    try:
        valor = float(item.get("valorTotalEstimado") or 0)
        if valor >= 2_000_000:
            score += 28
        elif valor >= 500_000:
            score += 18
        elif valor > 0:
            score += 9
    except Exception:
        pass
    modalidade = int(item.get("codigoModalidadeContratacao") or 0)
    if modalidade == 6:
        score += 10
    elif modalidade == 4:
        score += 8
    elif modalidade == 8:
        score += 6
    texto = " ".join([str(item.get("objetoCompra") or ""), str(item.get("informacaoComplementar") or "")]).lower()
    if termo:
        termo_lower = termo.lower().strip()
        if termo_lower in texto:
            score += 32
        for token in [t for t in termo_lower.split() if len(t) >= 3]:
            if token in texto:
                score += 5
    return score


def normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    unidade = item.get("unidadeOrgao") or {}
    orgao = item.get("orgaoEntidade") or {}
    municipio = unidade.get("municipioNome") or orgao.get("municipioNome") or "Município não informado"
    uf = unidade.get("ufSigla") or orgao.get("ufSigla") or "UF"
    modalidade_cod = item.get("codigoModalidadeContratacao")
    modalidade = MODALIDADES.get(modalidade_cod, item.get("modalidadeNome") or "Modalidade não informada")
    objeto = item.get("objetoCompra") or "Objeto não informado"
    fonte = item.get("linkSistemaOrigem") or item.get("linkProcessoEletronico") or item.get("url") or ""
    niche = detect_niche(objeto)
    valor = item.get("valorTotalEstimado")
    encerramento = item.get("dataEncerramentoProposta") or item.get("dataEncerramentoRecebimentoProposta")
    return {
        "id": item.get("numeroControlePNCP") or item.get("numeroCompra") or f"{municipio}-{modalidade_cod}-{objeto[:24]}",
        "objeto": objeto,
        "orgao": orgao.get("razaoSocial") or unidade.get("nomeUnidade") or "Órgão não informado",
        "municipio": municipio,
        "uf": uf,
        "modalidade": modalidade,
        "modalidade_codigo": modalidade_cod,
        "valor": valor,
        "valor_formatado": money_br(valor),
        "abertura": item.get("dataAberturaProposta") or item.get("dataPublicacaoPncp"),
        "encerramento": encerramento,
        "urgencia": urgency_label(encerramento),
        "fonte": fonte,
        "nicho": niche,
        "score": 0,
        "raw": item,
    }


def _request(path: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    response = requests.get(f"{API_BASE}/{path}", params=params, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    payload = response.json()
    data = payload.get("data") if isinstance(payload, dict) else payload
    return data if isinstance(data, list) else []


@st.cache_data(ttl=45, show_spinner=False)
def test_connection() -> Dict[str, Any]:
    start = datetime.now()
    try:
        rows = _request("proposta", {"pagina": 1, "tamanhoPagina": 1})
        ms = int((datetime.now() - start).total_seconds() * 1000)
        return {"ok": True, "latency_ms": ms, "sample": len(rows)}
    except Exception as exc:
        ms = int((datetime.now() - start).total_seconds() * 1000)
        return {"ok": False, "latency_ms": ms, "error": str(exc)}


@st.cache_data(ttl=70, show_spinner=False)
def fetch_feed(
    termo: str = "",
    uf: str = "Todas",
    modalidades: Optional[List[int]] = None,
    endpoint: str = "proposta",
    max_per_modality: int = 6,
    page_size: int = 10,
    niche_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    modalidades = modalidades or FAST_HOME_MODALIDADES
    termo = (termo or "").strip()

    def worker(modalidade: int) -> List[Dict[str, Any]]:
        params = {"codigoModalidadeContratacao": modalidade, "pagina": 1, "tamanhoPagina": page_size}
        data = _request(endpoint, params)
        items = [normalize_item(x) for x in data]
        if uf != "Todas":
            items = [x for x in items if str(x.get("uf", "")).upper() == uf.upper()]
        if termo:
            tokens = [t.lower() for t in termo.split() if len(t) >= 3]
            filtered = []
            for row in items:
                hay = f"{row['objeto']} {row['orgao']} {row['municipio']} {row['uf']} {row['nicho']}".lower()
                if termo.lower() in hay or any(tok in hay for tok in tokens):
                    filtered.append(row)
            items = filtered
        if niche_filter:
            items = [x for x in items if x.get("nicho") == niche_filter]
        for row in items:
            row["score"] = score_item(row["raw"], termo)
        items.sort(key=lambda x: (x.get("score", 0), x.get("valor") or 0), reverse=True)
        return items[:max_per_modality]

    results: List[Dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(modalidades))) as ex:
        futures = {ex.submit(worker, mod): mod for mod in modalidades}
        for future in as_completed(futures):
            try:
                results.extend(future.result())
            except Exception:
                continue

    dedup: Dict[str, Dict[str, Any]] = {}
    for item in results:
        key = str(item.get("id"))
        prev = dedup.get(key)
        if not prev or item.get("score", 0) > prev.get("score", 0):
            dedup[key] = item

    final = list(dedup.values())
    final.sort(key=lambda x: (x.get("score", 0), x.get("valor") or 0), reverse=True)
    return final


def export_df(items: List[Dict[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "objeto": x["objeto"],
            "orgao": x["orgao"],
            "municipio": x["municipio"],
            "uf": x["uf"],
            "modalidade": x["modalidade"],
            "valor_estimado": x["valor_formatado"],
            "abertura": date_br(x["abertura"]),
            "encerramento": date_br(x["encerramento"]),
            "urgencia": x["urgencia"],
            "nicho": x["nicho"],
            "link": x["fonte"],
        }
        for x in items
    ])


def render_cards(items: List[Dict[str, Any]], columns: int = 3) -> None:
    if not items:
        st.info("Nenhuma licitação encontrada para este recorte no momento.")
        return
    cols = st.columns(columns)
    for idx, item in enumerate(items):
        lead = "Alta chance de captura comercial" if float(item.get("valor") or 0) >= 300_000 else "Boa vitrine para prospecção"
        with cols[idx % columns]:
            btn = f'<a class="btn-link" href="{item["fonte"]}" target="_blank">Abrir origem</a>' if item.get("fonte") else ""
            st.markdown(
                f"""
                <div class="card">
                  <div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start;">
                    <h3>{item['objeto']}</h3>
                    {urgency_html(item.get('encerramento'))}
                  </div>
                  <div class="card-orgao">{item['orgao']}</div>
                  <div class="chips">
                    <span class="chip">📍 {item['municipio']}/{item['uf']}</span>
                    <span class="chip">⚖️ {item['modalidade']}</span>
                    <span class="chip">🏷️ {item['nicho']}</span>
                  </div>
                  <div class="meta">
                    <div class="meta-box"><div class="meta-label">Valor estimado</div><div class="meta-value">{item['valor_formatado']}</div></div>
                    <div class="meta-box"><div class="meta-label">Encerramento</div><div class="meta-value">{date_br(item['encerramento'])}</div></div>
                  </div>
                  <div class="small">{lead}</div>
                  <div class="actions">
                    <span class="muted">MS Radar • live no PNCP</span>
                    {btn}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def kpis_for(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "total": len(items),
        "urgentes": sum(1 for x in items if (days_left(x.get("encerramento")) is not None and 0 <= days_left(x.get("encerramento")) <= 3)),
        "alto_valor": sum(1 for x in items if float(x.get("valor") or 0) >= 300_000),
        "ufs": len({x.get("uf") for x in items if x.get("uf")}),
        "valor_total": sum(float(x.get("valor") or 0) for x in items if str(x.get("valor") or "").strip()),
    }


def filter_urgent(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [x for x in items if x.get("urgencia") in {"Encerra hoje", "Prazo curto"}]


def filter_high_value(items: List[Dict[str, Any]], min_value: float = 300_000) -> List[Dict[str, Any]]:
    return [x for x in items if float(x.get("valor") or 0) >= min_value]


def top_by_state(items: List[Dict[str, Any]], uf: str, limit: int = 6) -> List[Dict[str, Any]]:
    return [x for x in items if str(x.get("uf") or "").upper() == uf.upper()][:limit]


def top_by_niche(items: List[Dict[str, Any]], niche: str, limit: int = 6) -> List[Dict[str, Any]]:
    return [x for x in items if x.get("nicho") == niche][:limit]
