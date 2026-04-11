from __future__ import annotations

import pandas as pd
import streamlit as st

from app.core.utils import money


def set_page(title: str, icon: str = '📡') -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout='wide', initial_sidebar_state='expanded')
    inject_css()


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1rem; padding-bottom: 2rem; max-width: 1450px;}
        .hero {
            background: linear-gradient(135deg, #081322 0%, #0f2d4d 45%, #136f63 100%);
            border-radius: 28px; color: white; padding: 30px 34px; margin-bottom: 18px;
            box-shadow: 0 20px 48px rgba(8, 19, 34, .18);
        }
        .hero h1 {margin: 0; font-size: 2rem; line-height:1.1;}
        .hero p {margin: .55rem 0 0 0; opacity: .95; font-size: 1rem;}
        .kpi {
            background: white; border: 1px solid #e2e8f0; border-radius: 22px;
            padding: 18px; box-shadow: 0 10px 24px rgba(15,23,42,.05); min-height: 110px;
        }
        .kpi .label {font-size: .82rem; color:#64748b; text-transform: uppercase; letter-spacing:.03em;}
        .kpi .value {font-size: 1.7rem; font-weight: 700; color:#0f172a; margin-top: 6px;}
        .kpi .sub {font-size:.88rem; color:#475569; margin-top: 4px;}
        .card {
            background:white; border:1px solid #e2e8f0; border-radius:22px; padding:18px; margin-bottom:14px;
            box-shadow: 0 10px 26px rgba(15,23,42,.05);
        }
        .card-title {font-size:1.12rem; font-weight:700; color:#0f172a; margin-bottom:.35rem;}
        .pill {display:inline-block; padding: .28rem .65rem; border-radius: 999px; background:#eff6ff; color:#1d4ed8; font-size:.78rem; margin:0 .35rem .35rem 0;}
        .pill-green {background:#ecfdf5; color:#047857;}
        .pill-amber {background:#fffbeb; color:#b45309;}
        .pill-red {background:#fef2f2; color:#b91c1c;}
        .score-circle {background:#0f766e; color:white; width:78px; height:78px; border-radius:999px; display:flex; align-items:center; justify-content:center; font-size:1.5rem; font-weight:700; margin:0 auto 8px auto;}
        .status-ok, .status-error {
            border-radius: 18px; padding: 14px 16px; margin-bottom: 16px; font-size: .95rem; border:1px solid;
        }
        .status-ok {background:#ecfdf5; color:#065f46; border-color:#a7f3d0;}
        .status-error {background:#fef2f2; color:#991b1b; border-color:#fecaca;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(f"<div class='hero'><h1>{title}</h1><p>{subtitle}</p></div>", unsafe_allow_html=True)


def kpi(label: str, value: str, sub: str = '') -> None:
    st.markdown(
        f"<div class='kpi'><div class='label'>{label}</div><div class='value'>{value}</div><div class='sub'>{sub}</div></div>",
        unsafe_allow_html=True,
    )


def connection_banner(ok: bool, message: str, elapsed_seconds: float | None = None) -> None:
    klass = 'status-ok' if ok else 'status-error'
    extra = f' · tempo={elapsed_seconds}s' if elapsed_seconds is not None else ''
    st.markdown(f"<div class='{klass}'><strong>PNCP ao vivo</strong> — {message}{extra}</div>", unsafe_allow_html=True)


def opportunity_card(row: dict) -> None:
    score = row.get('oportunidade_score', 0)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    left, right = st.columns([5, 1.3])
    with left:
        st.markdown(f"<div class='card-title'>{row.get('resumo_objeto') or row.get('objeto_compra') or 'Oportunidade sem título'}</div>", unsafe_allow_html=True)
        st.caption(f"{row.get('orgao_razao_social','Órgão não informado')} · {row.get('municipio_nome','')} / {row.get('uf_sigla','')}")
        chips = [
            row.get('modalidade_nome') or 'Modalidade não informada',
            f"Prazo: {(row.get('data_encerramento_proposta') or '—')[:10]}",
            f"Valor: {money(row.get('valor_total_estimado'))}",
        ]
        if row.get('is_open_proposal'):
            chips.append('Recebimento aberto')
        if row.get('nichos'):
            chips.extend(row['nichos'][:2])
        for chip in chips:
            klass = 'pill'
            if chip == 'Recebimento aberto':
                klass = 'pill pill-green'
            elif chip.startswith('Prazo:') and chip[7:17] != '—':
                klass = 'pill pill-amber'
            st.markdown(f"<span class='{klass}'>{chip}</span>", unsafe_allow_html=True)
        st.write(row.get('objeto_compra') or 'Sem descrição do objeto.')
        links = []
        if row.get('link_sistema_origem'):
            links.append(f"[Abrir sistema de origem]({row['link_sistema_origem']})")
        if row.get('link_processo_eletronico'):
            links.append(f"[Abrir processo eletrônico]({row['link_processo_eletronico']})")
        if links:
            st.markdown(' · '.join(links))
        st.caption(f"Controle PNCP: {row.get('numero_controle_pncp')} · Processo: {row.get('processo') or '—'}")
    with right:
        st.markdown(f"<div class='score-circle'>{score:.0f}</div>", unsafe_allow_html=True)
        st.metric('Urgência', f"{row.get('urgencia_score', 0):.0f}")
        st.metric('Valor', f"{row.get('valor_score', 0):.0f}")
        st.metric('Risco', f"{row.get('risco_score', 0):.0f}")
    st.markdown('</div>', unsafe_allow_html=True)


def rows_to_df(rows) -> pd.DataFrame:
    return pd.DataFrame([dict(r) if not isinstance(r, dict) else r for r in rows])
