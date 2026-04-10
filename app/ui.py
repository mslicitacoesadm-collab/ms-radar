from __future__ import annotations

import pandas as pd
import streamlit as st

from app.core.utils import money


def set_page(title: str, icon: str = '🎯') -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout='wide', initial_sidebar_state='expanded')
    inject_css()


def inject_css() -> None:
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
        .hero {
            background: linear-gradient(135deg, #0f172a 0%, #134e4a 55%, #0f766e 100%);
            border-radius: 24px; color: white; padding: 28px 32px; margin-bottom: 18px;
            box-shadow: 0 18px 40px rgba(15, 23, 42, .16);
        }
        .hero h1 {margin: 0; font-size: 2rem;}
        .hero p {margin: .35rem 0 0 0; opacity: .92;}
        .kpi {
            background: white; border: 1px solid #e2e8f0; border-radius: 22px;
            padding: 18px; box-shadow: 0 8px 24px rgba(15,23,42,.05);
        }
        .kpi .label {font-size: .85rem; color:#64748b;}
        .kpi .value {font-size: 1.6rem; font-weight: 700; color:#0f172a;}
        .pill {display:inline-block; padding: .22rem .6rem; border-radius: 999px; background:#ecfeff; color:#155e75; font-size:.8rem; margin-right:.35rem;}
        .card {
            background:white; border:1px solid #e2e8f0; border-radius:22px; padding:18px; margin-bottom:14px;
            box-shadow: 0 10px 26px rgba(15,23,42,.05);
        }
        .score {font-size: 1.5rem; font-weight:700; color:#0f766e;}
        .muted {color:#64748b; font-size:.92rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str) -> None:
    st.markdown(f"<div class='hero'><h1>{title}</h1><p>{subtitle}</p></div>", unsafe_allow_html=True)


def kpi(label: str, value: str, help_text: str = '') -> None:
    st.markdown(
        f"<div class='kpi'><div class='label'>{label}</div><div class='value'>{value}</div><div class='muted'>{help_text}</div></div>",
        unsafe_allow_html=True,
    )


def opportunity_card(row: dict) -> None:
    score = row.get('oportunidade_score', 0)
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    c1, c2 = st.columns([5, 1.3])
    with c1:
        st.markdown(f"### {row.get('resumo_objeto') or row.get('objeto_compra')}")
        st.caption(f"{row.get('orgao_razao_social','')} · {row.get('municipio_nome','')} / {row.get('uf_sigla','')}")
        chips = [
            row.get('modalidade_nome') or 'Modalidade não informada',
            f"Encerra: {str(row.get('data_encerramento_proposta') or '—')[:10]}",
            f"Valor: {money(row.get('valor_total_estimado'))}",
        ]
        st.markdown(' '.join([f"<span class='pill'>{chip}</span>" for chip in chips]), unsafe_allow_html=True)
        st.write(row.get('objeto_compra') or 'Sem descrição disponível.')
        links = []
        if row.get('link_sistema_origem'):
            links.append(f"[Sistema de origem]({row['link_sistema_origem']})")
        if row.get('link_processo_eletronico'):
            links.append(f"[Processo eletrônico]({row['link_processo_eletronico']})")
        if links:
            st.markdown(' · '.join(links))
        st.caption(f"PNCP: {row.get('numero_controle_pncp')} · Processo: {row.get('processo') or '—'}")
    with c2:
        st.markdown(f"<div class='score'>{score:.0f}</div><div class='muted'>score</div>", unsafe_allow_html=True)
        st.metric('Urgência', f"{row.get('urgencia_score', 0):.0f}")
        st.metric('Aderência', f"{row.get('aderencia_score', 0):.0f}")
    st.markdown("</div>", unsafe_allow_html=True)


def rows_to_df(rows) -> pd.DataFrame:
    data = [dict(r) if not isinstance(r, dict) else r for r in rows]
    return pd.DataFrame(data)
