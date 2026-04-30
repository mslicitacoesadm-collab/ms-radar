from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from core.pncp import (
    MODALIDADES,
    advanced_search,
    aggregate,
    days_to_deadline,
    filter_items,
    live_home_feed,
    unique,
)

st.set_page_config(page_title="MS Radar", page_icon="📡", layout="wide", initial_sidebar_state="collapsed")

PRIMARY = "#B42318"
DARK = "#111827"
MUTED = "#6B7280"
BG = "#F6F7F9"
BORDER = "#E5E7EB"
LOGO = Path("assets/logo_ms_radar.png")


def css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background:{BG}; color:{DARK}; }}
        [data-testid="stSidebar"] {{ display:none; }}
        .block-container {{ max-width:1180px; padding-top:1rem; padding-bottom:2rem; }}
        .hero {{ background:linear-gradient(135deg,#fff 0%,#fff 62%,#fff4f2 100%); border:1px solid {BORDER}; border-radius:28px; padding:22px; box-shadow:0 12px 32px rgba(17,24,39,.06); margin-bottom:18px; }}
        .title {{ font-size:2.05rem; font-weight:900; line-height:1.08; letter-spacing:-.035em; margin:0; color:{DARK}; }}
        .sub {{ color:{MUTED}; font-size:1rem; margin-top:.55rem; max-width:760px; }}
        .badge {{ display:inline-flex; align-items:center; gap:.35rem; padding:.38rem .72rem; border:1px solid {BORDER}; border-radius:999px; background:#fff; color:{DARK}; font-size:.82rem; margin:.25rem .25rem .25rem 0; }}
        .badge-red {{ background:#fff1f0; border-color:#ffd5d2; color:{PRIMARY}; }}
        .metric {{ background:#fff; border:1px solid {BORDER}; border-radius:20px; padding:14px 16px; box-shadow:0 8px 24px rgba(17,24,39,.045); }}
        .metric b {{ font-size:1.45rem; color:{DARK}; display:block; }}
        .metric span {{ color:{MUTED}; font-size:.84rem; }}
        .section {{ font-size:1.17rem; font-weight:850; margin:1rem 0 .55rem; letter-spacing:-.015em; }}
        .card {{ background:#fff; border:1px solid {BORDER}; border-radius:22px; padding:15px; min-height:245px; box-shadow:0 8px 24px rgba(17,24,39,.045); margin-bottom:12px; }}
        .card:hover {{ border-color:#f2b8b5; box-shadow:0 12px 30px rgba(180,35,24,.08); }}
        .obj {{ font-weight:850; line-height:1.25; font-size:1rem; margin:.3rem 0 .5rem; color:{DARK}; }}
        .meta {{ color:{MUTED}; font-size:.84rem; margin:.18rem 0; }}
        .tag {{ display:inline-block; border:1px solid {BORDER}; background:#F9FAFB; color:{DARK}; padding:.21rem .52rem; border-radius:999px; font-size:.72rem; margin:0 .25rem .3rem 0; }}
        .urgent {{ background:#fff1f0; border-color:#ffd5d2; color:{PRIMARY}; font-weight:700; }}
        .navbox {{ background:#fff; border:1px solid {BORDER}; border-radius:22px; padding:12px; margin:.2rem 0 1rem; box-shadow:0 8px 24px rgba(17,24,39,.04); }}
        .statebox {{ background:#fff; border:1px solid {BORDER}; border-radius:20px; padding:14px; text-align:center; margin-bottom:12px; }}
        .statebox b {{ font-size:1.35rem; color:{PRIMARY}; }}
        .small {{ color:{MUTED}; font-size:.86rem; }}
        .pagebox {{ background:#fff; border:1px solid {BORDER}; border-radius:999px; text-align:center; padding:.65rem; color:{MUTED}; }}
        div.stButton > button {{ border-radius:999px; border:1px solid {BORDER}; background:#fff; color:{DARK}; font-weight:650; }}
        div.stButton > button:hover {{ border-color:{PRIMARY}; color:{PRIMARY}; }}
        div[data-testid="stRadio"] label p {{ font-weight:700; }}
        .stLinkButton a {{ border-radius:999px !important; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=120, show_spinner=False)
def cached_home(uf: str = ""):
    return live_home_feed(limit=12, uf=uf, timeout=4.5)


@st.cache_data(ttl=90, show_spinner=False)
def cached_search(query: str, uf: str, modalidade: int | None, endpoint: str, pages: int):
    return advanced_search(query=query, uf=uf, modalidade=modalidade, endpoint=endpoint, pages=pages, page_size=20)


def fmt_money(v: Any) -> str:
    if v in (None, ""):
        return "Não informado"
    try:
        return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "Não informado"


def fmt_date(v: str | None) -> str:
    if not v:
        return "Não informada"
    try:
        return datetime.strptime(v[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except Exception:
        return v


def card(item: dict[str, Any]) -> None:
    dias = days_to_deadline(item)
    tags = []
    if dias is not None:
        if dias < 0:
            tags.append('<span class="tag">Prazo vencido</span>')
        elif dias == 0:
            tags.append('<span class="tag urgent">Encerra hoje</span>')
        elif dias <= 3:
            tags.append('<span class="tag urgent">Prazo curto</span>')
    if item.get("estimated_value") and float(item.get("estimated_value") or 0) >= 100000:
        tags.append('<span class="tag urgent">Alto valor</span>')
    tags.append(f'<span class="tag">{item.get("modality") or "Modalidade"}</span>')
    title = item.get("title") or "Licitação sem título informado"
    obj = item.get("object_text") or ""
    st.markdown(
        f"""
        <div class="card">
            <div>{''.join(tags)}</div>
            <div class="obj">{title[:230]}</div>
            <div class="meta"><b>Órgão:</b> {item.get('agency') or 'Não informado'}</div>
            <div class="meta"><b>Local:</b> {item.get('city') or 'Não informado'} / {item.get('state') or '--'}</div>
            <div class="meta"><b>Encerramento:</b> {fmt_date(item.get('deadline_date'))}</div>
            <div class="meta"><b>Valor:</b> {fmt_money(item.get('estimated_value'))}</div>
            <div class="meta" style="margin-top:.45rem;">{obj[:160]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.link_button("Ver no PNCP / origem", item.get("source_url") or "https://pncp.gov.br/app/editais", use_container_width=True)


def paginate(items: list[dict[str, Any]], key: str, per_page: int = 9) -> None:
    if not items:
        st.warning("Nenhuma licitação encontrada para esse recorte.")
        return
    pages = max(1, (len(items) + per_page - 1) // per_page)
    skey = f"page_{key}"
    st.session_state.setdefault(skey, 1)
    st.session_state[skey] = max(1, min(int(st.session_state[skey]), pages))
    page = st.session_state[skey]
    start = (page - 1) * per_page
    chunk = items[start:start + per_page]
    cols = st.columns(3)
    for i, item in enumerate(chunk):
        with cols[i % 3]:
            card(item)
    c1, c2, c3 = st.columns([1, 2, 1])
    with c1:
        if st.button("← Anterior", key=f"prev_{key}", disabled=page <= 1, use_container_width=True):
            st.session_state[skey] = page - 1
            st.rerun()
    with c2:
        st.markdown(f"<div class='pagebox'>Página <b>{page}</b> de <b>{pages}</b> · {len(items)} resultados</div>", unsafe_allow_html=True)
    with c3:
        if st.button("Próxima →", key=f"next_{key}", disabled=page >= pages, use_container_width=True):
            st.session_state[skey] = page + 1
            st.rerun()


def header() -> None:
    st.markdown('<div class="hero">', unsafe_allow_html=True)
    left, right = st.columns([1, 2.7])
    with left:
        if LOGO.exists():
            st.image(str(LOGO), width=245)
        else:
            st.markdown("# MS Radar")
    with right:
        st.markdown('<h1 class="title">Busque licitações com rapidez, sem bagunça e sem base desatualizada.</h1>', unsafe_allow_html=True)
        st.markdown('<div class="sub">Consulta em modo espelho: o sistema busca no PNCP, apresenta em cards limpos e mantém a entrada leve para uso diário.</div>', unsafe_allow_html=True)
        st.markdown('<span class="badge badge-red">PNCP ao vivo</span><span class="badge">Sem banco de licitações</span><span class="badge">Interface clean</span>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def nav() -> str:
    st.markdown('<div class="navbox">', unsafe_allow_html=True)
    view = st.radio(
        "Navegação",
        ["Início", "Por Estado", "Por Cidade", "Por Modalidade", "Filtro Avançado"],
        horizontal=True,
        label_visibility="collapsed",
        key="view",
    )
    st.markdown('</div>', unsafe_allow_html=True)
    return view


def metrics(items: list[dict[str, Any]], source_msg: str, elapsed: int) -> None:
    urg = len([x for x in items if days_to_deadline(x) is not None and 0 <= days_to_deadline(x) <= 3])
    ba = len([x for x in items if x.get("state") == "BA"])
    val = len([x for x in items if x.get("estimated_value")])
    data = [("Resultados", len(items)), ("Prazo curto", urg), ("Bahia", ba), ("Com valor", val)]
    cols = st.columns(4)
    for col, (label, value) in zip(cols, data):
        with col:
            st.markdown(f"<div class='metric'><b>{value}</b><span>{label}</span></div>", unsafe_allow_html=True)
    st.caption(f"{source_msg} Tempo da última consulta: {elapsed} ms. Cache temporário: 120s.")


def quick_filters(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    q1, q2, q3, q4 = st.columns([2.2, .8, 1.1, 1.2])
    with q1:
        q = st.text_input("Busca rápida", placeholder="Ex.: combustível, merenda, pneus, limpeza")
    with q2:
        uf = st.selectbox("UF", [""] + unique(items, "state"), format_func=lambda x: x or "Todas")
    with q3:
        city = st.selectbox("Cidade", [""] + unique(items, "city"), format_func=lambda x: x or "Todas")
    with q4:
        mod = st.selectbox("Modalidade", [""] + unique(items, "modality"), format_func=lambda x: x or "Todas")
    return filter_items(items, query=q, uf=uf, city=city, modality=mod)


def main() -> None:
    css()
    header()
    view = nav()

    if "home_uf" not in st.session_state:
        st.session_state.home_uf = ""

    # Carrega automaticamente ao entrar, mas com limite curto e cache.
    with st.spinner("Carregando vitrine rápida do PNCP..."):
        result = cached_home(st.session_state.home_uf)
    notices = result.notices

    if not result.ok:
        st.error(result.message)
        st.info("A tela continua funcionando. Use o Filtro Avançado para tentar uma consulta direta com menos filtros ou confira se o PNCP está respondendo no seu ambiente.")

    filtered = quick_filters(notices)
    metrics(filtered, result.message, result.elapsed_ms)

    if view == "Início":
        st.markdown('<div class="section">Vitrine rápida</div>', unsafe_allow_html=True)
        paginate(filtered, "home", 9)

    elif view == "Por Estado":
        st.markdown('<div class="section">Por Estado</div>', unsafe_allow_html=True)
        rows = aggregate(filtered, "state")
        cols = st.columns(4)
        for i, row in enumerate(rows):
            uf = row["state"]
            total = row["total"]
            with cols[i % 4]:
                st.markdown(f"<div class='statebox'><b>{uf}</b><br><span class='small'>{total} licitações</span></div>", unsafe_allow_html=True)
                if st.button(f"Abrir {uf}", key=f"open_{uf}", use_container_width=True):
                    st.session_state.selected_uf = uf
                    st.rerun()
        selected = st.session_state.get("selected_uf", "")
        if selected:
            st.markdown(f'<div class="section">Licitações em {selected}</div>', unsafe_allow_html=True)
            paginate(filter_items(filtered, uf=selected), f"uf_{selected}", 9)

    elif view == "Por Cidade":
        st.markdown('<div class="section">Por Cidade</div>', unsafe_allow_html=True)
        city_rows = aggregate(filtered, "city")[:32]
        cols = st.columns(4)
        for i, row in enumerate(city_rows):
            city = row["city"]
            with cols[i % 4]:
                st.markdown(f"<div class='statebox'><b style='font-size:1rem'>{city}</b><br><span class='small'>{row['total']} licitações</span></div>", unsafe_allow_html=True)
                if st.button("Ver lista", key=f"city_{i}_{city}", use_container_width=True):
                    st.session_state.selected_city = city
                    st.rerun()
        if st.session_state.get("selected_city"):
            city = st.session_state.selected_city
            st.markdown(f'<div class="section">Licitações em {city}</div>', unsafe_allow_html=True)
            paginate(filter_items(filtered, city=city), f"city_{city}", 9)

    elif view == "Por Modalidade":
        st.markdown('<div class="section">Por Modalidade</div>', unsafe_allow_html=True)
        rows = aggregate(filtered, "modality")
        cols = st.columns(3)
        for i, row in enumerate(rows):
            modality = row["modality"]
            with cols[i % 3]:
                st.markdown(f"<div class='statebox'><b style='font-size:1rem'>{modality}</b><br><span class='small'>{row['total']} licitações</span></div>", unsafe_allow_html=True)
                if st.button("Abrir modalidade", key=f"mod_{i}_{modality}", use_container_width=True):
                    st.session_state.selected_modality = modality
                    st.rerun()
        if st.session_state.get("selected_modality"):
            mod = st.session_state.selected_modality
            st.markdown(f'<div class="section">{mod}</div>', unsafe_allow_html=True)
            paginate(filter_items(filtered, modality=mod), f"modality_{mod}", 9)

    else:
        st.markdown('<div class="section">Filtro Avançado</div>', unsafe_allow_html=True)
        st.caption("Essa busca é sob demanda para não deixar a entrada lenta.")
        a, b, c, d = st.columns([2, .8, 1.4, 1])
        with a:
            q = st.text_input("Termo", placeholder="Ex.: transporte escolar, material de construção")
        with b:
            uf = st.text_input("UF", max_chars=2, placeholder="BA")
        with c:
            mod_name = st.selectbox("Modalidade", ["Todas"] + [f"{k} - {v}" for k, v in MODALIDADES.items()])
        with d:
            endpoint = st.selectbox("Tipo", ["proposta", "publicacao"], format_func=lambda x: "Propostas abertas" if x == "proposta" else "Publicações recentes")
        pages = st.slider("Profundidade da busca", 1, 3, 1, help="Quanto maior, mais resultados, porém mais lento.")
        modalidade = None if mod_name == "Todas" else int(mod_name.split(" - ", 1)[0])
        if st.button("Buscar agora", type="primary", use_container_width=True):
            with st.spinner("Consultando PNCP..."):
                res = cached_search(q, uf.upper().strip(), modalidade, endpoint, pages)
            st.session_state.advanced_result = res
        if st.session_state.get("advanced_result"):
            res = st.session_state.advanced_result
            st.success(f"{res.message} Tempo: {res.elapsed_ms} ms") if res.ok else st.warning(res.message)
            paginate(res.notices, "advanced", 9)
            if res.notices:
                df = pd.DataFrame([{k: v for k, v in x.items() if k != "raw"} for x in res.notices])
                st.download_button("Baixar CSV", df.to_csv(index=False).encode("utf-8-sig"), "ms_radar_resultados.csv", "text/csv", use_container_width=True)

    st.markdown("<div class='small' style='text-align:center;margin-top:18px;'>MS Radar · consulta em tempo real ao PNCP · sem armazenamento persistente de licitações.</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
