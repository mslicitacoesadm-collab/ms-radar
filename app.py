from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from core.pncp import (
    aggregate_by_key,
    apply_filters,
    days_to_deadline,
    fetch_home_feed,
    probe_connection,
    top_urgent,
    top_value,
    unique_values,
)

st.set_page_config(page_title='MS Radar', page_icon='📡', layout='wide')

PRIMARY = '#B22222'
BG = '#F6F7F9'
CARD = '#FFFFFF'
TEXT = '#111827'
MUTED = '#6B7280'
BORDER = '#E5E7EB'
LOGO = Path('assets/logo_ms_radar.png')


def inject_css() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{ background: {BG}; color: {TEXT}; }}
        [data-testid="stSidebar"] {{ display: none; }}
        .block-container {{ padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1180px; }}
        .top-shell {{ background: linear-gradient(180deg,#ffffff 0%, #fbfbfc 100%); border:1px solid {BORDER}; border-radius:24px; padding: 18px 22px; box-shadow: 0 10px 30px rgba(17,24,39,0.05); margin-bottom: 18px; }}
        .hero-title {{ font-size: 2rem; font-weight: 800; line-height: 1.1; letter-spacing:-0.02em; margin:0; }}
        .hero-sub {{ color: {MUTED}; margin-top: .55rem; font-size: 1rem; }}
        .pill-row {{ display:flex; gap:.5rem; flex-wrap:wrap; margin-top:.9rem; }}
        .pill {{ background:#fff; border:1px solid {BORDER}; color:{TEXT}; padding:.45rem .8rem; border-radius:999px; font-size:.85rem; }}
        .section-title {{ font-size: 1.2rem; font-weight: 700; margin: 1rem 0 .7rem 0; }}
        .metric-card {{ background:{CARD}; border:1px solid {BORDER}; border-radius:20px; padding:16px 18px; box-shadow: 0 8px 24px rgba(17,24,39,0.04); }}
        .metric-value {{ font-size:1.45rem; font-weight:800; }}
        .metric-label {{ color:{MUTED}; font-size:.92rem; margin-top:4px; }}
        .notice-card {{ background:{CARD}; border:1px solid {BORDER}; border-radius:22px; padding:16px 18px; box-shadow: 0 8px 24px rgba(17,24,39,0.05); min-height: 228px; }}
        .notice-title {{ font-weight:700; font-size:1rem; line-height:1.35; margin-bottom:.55rem; }}
        .meta {{ color:{MUTED}; font-size:.88rem; margin-top:.18rem; }}
        .tag {{ display:inline-block; background:#fff5f5; color:{PRIMARY}; border:1px solid #f8d6d6; padding:.22rem .55rem; border-radius:999px; font-size:.76rem; font-weight:700; margin-right:.35rem; margin-bottom:.35rem; }}
        .tag-gray {{ display:inline-block; background:#f9fafb; color:{TEXT}; border:1px solid {BORDER}; padding:.22rem .55rem; border-radius:999px; font-size:.76rem; margin-right:.35rem; margin-bottom:.35rem; }}
        .soft-panel {{ background:{CARD}; border:1px solid {BORDER}; border-radius:22px; padding:14px 18px; box-shadow: 0 8px 24px rgba(17,24,39,0.04); }}
        div[data-testid="stHorizontalBlock"] .stButton > button {{ border-radius:999px; border:1px solid {BORDER}; background:#fff; }}
        .footer-note {{ color:{MUTED}; font-size:.86rem; text-align:center; margin-top:1rem; }}
        .pagination-note {{ color:{MUTED}; font-size:.85rem; margin-top:.4rem; }}
        .nav-caption {{ color:{MUTED}; font-size:.9rem; margin-top:.3rem; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def fmt_money(value: Any) -> str:
    if value in (None, ''):
        return 'Não informado'
    try:
        return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return 'Não informado'


def fmt_date(value: str | None) -> str:
    if not value:
        return 'Não informada'
    try:
        return datetime.strptime(value[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
    except Exception:
        return value


def render_notice_card(item: dict[str, Any]) -> None:
    dleft = days_to_deadline(item)
    urgency = ''
    if dleft is not None and dleft <= 1:
        urgency = '<span class="tag">Encerra hoje</span>'
    elif dleft is not None and dleft <= 3:
        urgency = '<span class="tag">Prazo curto</span>'
    st.markdown(
        f"""
        <div class="notice-card">
            <div>{urgency}<span class="tag-gray">{item.get('modality') or 'Modalidade não informada'}</span></div>
            <div class="notice-title">{item.get('title') or 'Licitação sem título'}</div>
            <div class="meta"><strong>Órgão:</strong> {item.get('agency') or 'Não informado'}</div>
            <div class="meta"><strong>Cidade/UF:</strong> {(item.get('city') or 'Não informada')} / {(item.get('state') or '--')}</div>
            <div class="meta"><strong>Valor estimado:</strong> {fmt_money(item.get('estimated_value'))}</div>
            <div class="meta"><strong>Encerramento:</strong> {fmt_date(item.get('deadline_date'))}</div>
            <div class="meta" style="margin-top:.55rem;">{(item.get('object_text') or '')[:180]}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if item.get('source_url'):
        st.link_button('Ver detalhes', item['source_url'], use_container_width=True)


def render_paginated_cards(items: list[dict[str, Any]], key: str, per_page: int = 9) -> None:
    total = len(items)
    pages = max(1, (total + per_page - 1) // per_page)
    state_key = f'page_{key}'
    if state_key not in st.session_state:
        st.session_state[state_key] = 1
    st.session_state[state_key] = max(1, min(st.session_state[state_key], pages))
    page = st.session_state[state_key]
    start = (page - 1) * per_page
    chunk = items[start:start + per_page]
    cols = st.columns(3)
    for idx, item in enumerate(chunk):
        with cols[idx % 3]:
            render_notice_card(item)
    nav1, nav2, nav3 = st.columns([1, 2, 1])
    with nav1:
        if st.button('← Anterior', key=f'prev_{key}', disabled=page <= 1, use_container_width=True):
            st.session_state[state_key] = page - 1
            st.rerun()
    with nav2:
        st.markdown(
            f"<div class='soft-panel' style='text-align:center; padding:.7rem 1rem;'><strong>Página {page}</strong> de {pages}<div class='pagination-note'>{total} licitações encontradas</div></div>",
            unsafe_allow_html=True,
        )
    with nav3:
        if st.button('Próxima →', key=f'next_{key}', disabled=page >= pages, use_container_width=True):
            st.session_state[state_key] = page + 1
            st.rerun()


def render_state_cards(notices: list[dict[str, Any]]) -> None:
    states = aggregate_by_key(notices, 'state')
    cols = st.columns(4)
    for idx, row in enumerate(states):
        uf = row['state']
        total = row['total']
        with cols[idx % 4]:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{uf}</div><div class='metric-label'>{total} licitações</div></div>",
                unsafe_allow_html=True,
            )
            if st.button(f'Ver {uf}', key=f'uf_{uf}', use_container_width=True):
                st.session_state['selected_uf'] = uf
                st.session_state['view'] = 'Por Estado'
                st.rerun()


def render_city_cards(notices: list[dict[str, Any]], uf: str = '') -> None:
    items = notices
    if uf:
        items = [n for n in items if n.get('state') == uf]
    cities = aggregate_by_key(items, 'city')[:24]
    cols = st.columns(4)
    for idx, row in enumerate(cities):
        city = row['city']
        total = row['total']
        with cols[idx % 4]:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value' style='font-size:1.05rem'>{city}</div><div class='metric-label'>{total} licitações</div></div>",
                unsafe_allow_html=True,
            )


def main() -> None:
    inject_css()
    st.session_state.setdefault('view', 'Início')

    ok, probe_message = probe_connection()
    feed = fetch_home_feed(limit=18)
    notices = feed.notices

    with st.container():
        st.markdown("<div class='top-shell'>", unsafe_allow_html=True)
        top1, top2 = st.columns([1, 2.6])
        with top1:
            if LOGO.exists():
                st.image(str(LOGO), width=260)
            else:
                st.markdown("## MS Radar")
        with top2:
            st.markdown("<h1 class='hero-title'>Licitações em tempo real, com leitura simples e profissional.</h1>", unsafe_allow_html=True)
            st.markdown("<div class='hero-sub'>Modelo espelho do PNCP, com navegação leve, filtros objetivos e vitrine pronta para uso diário.</div>", unsafe_allow_html=True)
            badge = 'PNCP online' if ok else 'Modo demonstração'
            st.markdown(f"<div class='pill-row'><span class='pill'>{badge}</span><span class='pill'>{feed.message}</span></div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    choice = st.radio(
        'Navegação principal',
        ['Início', 'Por Estado', 'Por Cidade', 'Por Modalidade', 'Filtro Avançado'],
        horizontal=True,
        label_visibility='collapsed',
        key='view',
    )
    st.markdown("<div class='nav-caption'>Estrutura inspirada em um fluxo direto de filtro → recorte → lista, como no Buscar Licitação, que organiza a navegação por Filtro avançado, Por Estado, Por Cidade e Por Modalidade. citeturn786986view0</div>", unsafe_allow_html=True)

    qcol1, qcol2, qcol3, qcol4 = st.columns([2.2, 1, 1, 1])
    with qcol1:
        quick_query = st.text_input('Busque por objeto, órgão ou cidade', placeholder='Ex.: limpeza, combustível, software, vigilância')
    ufs = unique_values(notices, 'state')
    cities = unique_values(notices, 'city')
    modalities = unique_values(notices, 'modality')
    with qcol2:
        quick_uf = st.selectbox('UF', [''] + ufs, format_func=lambda x: x or 'Todas')
    with qcol3:
        quick_city = st.selectbox('Cidade', [''] + cities, format_func=lambda x: x or 'Todas')
    with qcol4:
        quick_modality = st.selectbox('Modalidade', [''] + modalities, format_func=lambda x: x or 'Todas')

    filtered = apply_filters(notices, query=quick_query, uf=quick_uf, city=quick_city, modality=quick_modality)

    m1, m2, m3, m4 = st.columns(4)
    summary = [
        ('Resultados', len(filtered)),
        ('Encerra rápido', len([n for n in filtered if (days_to_deadline(n) is not None and days_to_deadline(n) <= 3)])),
        ('Bahia', len([n for n in filtered if n.get('state') == 'BA'])),
        ('Modalidades', len(set([n.get('modality') for n in filtered if n.get('modality')]))),
    ]
    for col, (label, value) in zip([m1, m2, m3, m4], summary):
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{value}</div><div class='metric-label'>{label}</div></div>", unsafe_allow_html=True)

    if choice == 'Início':
        st.markdown("<div class='section-title'>Vitrine principal</div>", unsafe_allow_html=True)
        render_paginated_cards(filtered, 'home', per_page=9)

        a, b = st.columns(2)
        with a:
            st.markdown("<div class='section-title'>Prazo curto</div>", unsafe_allow_html=True)
            urgent = top_urgent(filtered, 6)
            if urgent:
                for item in urgent[:3]:
                    render_notice_card(item)
            else:
                st.info('Sem licitações urgentes nesta vitrine.')
        with b:
            st.markdown("<div class='section-title'>Maior valor</div>", unsafe_allow_html=True)
            high = top_value(filtered, 6)
            if high:
                for item in high[:3]:
                    render_notice_card(item)
            else:
                st.info('Sem valores estimados disponíveis nesta vitrine.')

    elif choice == 'Por Estado':
        st.markdown("<div class='section-title'>Licitações por Estado</div>", unsafe_allow_html=True)
        st.markdown("<div class='soft-panel'>A referência trabalha esse recorte com cards por UF e ação de aprofundar. Aqui o MS Radar segue a mesma lógica, mas com visual mais limpo e foco em teste operacional. citeturn786986view0</div>", unsafe_allow_html=True)
        render_state_cards(filtered)
        selected = st.session_state.get('selected_uf', '')
        if selected:
            st.markdown(f"<div class='section-title'>UF selecionada: {selected}</div>", unsafe_allow_html=True)
            rows = apply_filters(filtered, uf=selected)
            render_paginated_cards(rows, 'state', per_page=9)

    elif choice == 'Por Cidade':
        st.markdown("<div class='section-title'>Licitações por Cidade</div>", unsafe_allow_html=True)
        render_city_cards(filtered, uf=quick_uf)
        if quick_city:
            rows = apply_filters(filtered, city=quick_city)
            st.markdown(f"<div class='section-title'>Cidade selecionada: {quick_city}</div>", unsafe_allow_html=True)
            render_paginated_cards(rows, 'city', per_page=9)
        else:
            st.info('Selecione uma cidade acima para abrir a lista detalhada.')

    elif choice == 'Por Modalidade':
        st.markdown("<div class='section-title'>Licitações por Modalidade</div>", unsafe_allow_html=True)
        mods = aggregate_by_key(filtered, 'modality')
        mod_cols = st.columns(3)
        for idx, row in enumerate(mods):
            modality = row['modality']
            total = row['total']
            with mod_cols[idx % 3]:
                st.markdown(f"<div class='metric-card'><div class='metric-value' style='font-size:1.05rem'>{modality}</div><div class='metric-label'>{total} licitações</div></div>", unsafe_allow_html=True)
        if quick_modality:
            rows = apply_filters(filtered, modality=quick_modality)
            st.markdown(f"<div class='section-title'>Modalidade selecionada: {quick_modality}</div>", unsafe_allow_html=True)
            render_paginated_cards(rows, 'modality', per_page=9)
        else:
            st.info('Selecione uma modalidade acima para abrir a lista detalhada.')

    else:
        st.markdown("<div class='section-title'>Filtro avançado</div>", unsafe_allow_html=True)
        adv1, adv2, adv3, adv4 = st.columns(4)
        with adv1:
            adv_only_ba = st.checkbox('Somente Bahia')
        with adv2:
            adv_value = st.selectbox('Faixa de valor', ['Todas', 'Até R$ 500 mil', 'R$ 500 mil a R$ 2 mi', 'Acima de R$ 2 mi'])
        with adv3:
            adv_deadline = st.selectbox('Prazo', ['Todos', 'Até 3 dias', 'Até 7 dias', 'Acima de 7 dias'])
        with adv4:
            export = st.button('Exportar CSV', use_container_width=True)
        rows = apply_filters(filtered, only_bahia=adv_only_ba)
        if adv_value != 'Todas':
            if adv_value == 'Até R$ 500 mil':
                rows = [r for r in rows if (r.get('estimated_value') or 0) <= 500_000]
            elif adv_value == 'R$ 500 mil a R$ 2 mi':
                rows = [r for r in rows if 500_000 < (r.get('estimated_value') or 0) <= 2_000_000]
            else:
                rows = [r for r in rows if (r.get('estimated_value') or 0) > 2_000_000]
        if adv_deadline != 'Todos':
            if adv_deadline == 'Até 3 dias':
                rows = [r for r in rows if (days_to_deadline(r) is not None and days_to_deadline(r) <= 3)]
            elif adv_deadline == 'Até 7 dias':
                rows = [r for r in rows if (days_to_deadline(r) is not None and days_to_deadline(r) <= 7)]
            else:
                rows = [r for r in rows if (days_to_deadline(r) is not None and days_to_deadline(r) > 7)]
        if export and rows:
            df = pd.DataFrame(rows)
            st.download_button('Baixar resultados filtrados', data=df.to_csv(index=False).encode('utf-8-sig'), file_name='ms_radar_filtro_avancado.csv', mime='text/csv')
        render_paginated_cards(rows, 'advanced', per_page=9)

    st.markdown(f"<div class='footer-note'>{probe_message} · Se a API do PNCP falhar, o app entra em modo demonstração para você validar o layout e o fluxo.</div>", unsafe_allow_html=True)


if __name__ == '__main__':
    main()
