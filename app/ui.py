from __future__ import annotations

import json
from datetime import datetime

import streamlit as st


def inject_css() -> None:
    st.markdown(
        '''
        <style>
        .block-container {padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1240px;}
        .hero-card, .metric-card, .result-card {
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            border: 1px solid rgba(20,71,230,.10);
            border-radius: 22px;
            padding: 1.1rem 1.2rem;
            box-shadow: 0 10px 30px rgba(15,23,42,.06);
        }
        .metric-value {font-size: 1.7rem; font-weight: 700; color: #0f172a;}
        .metric-label {font-size: .92rem; color: #475569;}
        .pill {
            display:inline-block; padding:.28rem .6rem; border-radius:999px; font-size:.78rem;
            background:#e8f0ff; color:#1447e6; border:1px solid rgba(20,71,230,.12); margin-right:.3rem;
        }
        .score-pill {
            display:inline-block; padding:.3rem .55rem; border-radius:999px; font-size:.78rem;
            background:#0f172a; color:white; margin-right:.35rem;
        }
        .soft {color:#475569; font-size:.94rem}
        .title-strong {font-size: 1.05rem; font-weight: 700; color:#0f172a; margin-bottom:.2rem;}
        .section-title {font-size:1.05rem; font-weight:700; color:#0f172a; margin:.2rem 0 .7rem 0;}
        </style>
        ''',
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, badges: list[str] | None = None) -> None:
    badges_html = ''.join(f'<span class="pill">{b}</span>' for b in (badges or []))
    st.markdown(
        f'''
        <div class="hero-card">
            <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap;">
                <div style="max-width:840px;">
                    <div style="font-size:2rem;font-weight:800;line-height:1.1;color:#0f172a;">{title}</div>
                    <div class="soft" style="margin-top:.5rem;">{subtitle}</div>
                    <div style="margin-top:.8rem;">{badges_html}</div>
                </div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, help_text: str = '') -> None:
    st.markdown(
        f'''
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="soft">{help_text}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def result_card(row) -> None:
    value = f"R$ {float(row.get('estimated_value', 0) or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    st.markdown(
        f'''
        <div class="result-card">
            <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap;">
                <div style="flex:1;min-width:280px;">
                    <div class="title-strong">{row.get('title','')}</div>
                    <div class="soft" style="margin-bottom:.5rem;">{row.get('agency','')} · {row.get('city','')} / {row.get('state','')}</div>
                    <div style="margin-bottom:.45rem;">
                        <span class="pill">{row.get('modality','')}</span>
                        <span class="pill">Prazo: {row.get('deadline_date','-')}</span>
                        <span class="pill">Publicação: {row.get('publication_date','-')}</span>
                    </div>
                    <div class="soft">{row.get('object_text','')}</div>
                </div>
                <div style="min-width:210px;">
                    <div style="margin-bottom:.45rem;">
                        <span class="score-pill">Oportunidade {row.get('opportunity_score',0)}</span>
                        <span class="score-pill">Fit {row.get('fit_score',0)}</span>
                    </div>
                    <div class="soft"><strong>Valor estimado:</strong> {value}</div>
                    <div class="soft"><strong>Motivo:</strong> {row.get('match_reason','')}</div>
                </div>
            </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )


def format_brl(value: float) -> str:
    return f"R$ {float(value or 0):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')


def json_download_button(data: dict, filename: str, label: str) -> None:
    st.download_button(label, data=json.dumps(data, ensure_ascii=False, indent=2), file_name=filename, mime='application/json')
