from __future__ import annotations

import streamlit as st

from app.core.config import DEFAULT_UFS, MODALIDADES, PNCP_DEFAULT_DAYS_BACK, PNCP_MAX_PAGES_PER_QUERY, PNCP_PAGE_SIZE
from app.core.live_service import build_export_dataframe, fetch_live_notices, format_query_summary, merge_endpoints, probe_connection_cached
from app.ui import connection_banner, hero, opportunity_card, set_page

set_page('Busca Suprema Live')
hero('Busca Suprema Live', 'Pesquisa em tempo real no PNCP, sem base local. Os filtros já disparam a consulta ao abrir e a cada alteração.')

probe = probe_connection_cached()
connection_banner(probe['ok'], probe['message'], probe['elapsed_seconds'])
if not probe['ok']:
    st.stop()

c1, c2, c3, c4 = st.columns([3.2, 1.1, 2.0, 1.4])
with c1:
    termo = st.text_input('Busca por objeto, nicho ou palavra-chave', placeholder='Ex.: material gráfico, combustível, merenda, software')
with c2:
    uf = st.selectbox('UF', DEFAULT_UFS)
with c3:
    municipio = st.text_input('Município', placeholder='Ex.: Salvador')
with c4:
    modalidade = st.selectbox('Modalidade', options=[0] + list(MODALIDADES.keys()), format_func=lambda x: 'Todas' if x == 0 else MODALIDADES[x])

c5, c6, c7, c8 = st.columns(4)
with c5:
    valor_min = st.number_input('Valor mínimo', min_value=0.0, value=0.0, step=1000.0)
with c6:
    valor_max = st.number_input('Valor máximo', min_value=0.0, value=0.0, step=1000.0)
with c7:
    only_open = st.toggle('Somente abertas', value=True)
with c8:
    sort_by = st.selectbox('Ordenar por', ['score', 'prazo', 'valor', 'recentes'], format_func=lambda x: {'score':'Melhor score', 'prazo':'Prazo mais próximo', 'valor':'Maior valor', 'recentes':'Mais recentes'}[x])

c9, c10, c11 = st.columns(3)
with c9:
    days_back = st.slider('Janela de dias', 1, 30, PNCP_DEFAULT_DAYS_BACK)
with c10:
    max_pages = st.slider('Máximo de páginas', 1, 6, PNCP_MAX_PAGES_PER_QUERY)
with c11:
    limit = st.select_slider('Quantidade de resultados', options=[20, 40, 60, 100], value=40)

with st.spinner('Consultando o PNCP em tempo real...'):
    payload_pub = fetch_live_notices(
        endpoint='publicacao',
        query=termo,
        uf=uf,
        municipio=municipio,
        modalidade_codigo=modalidade,
        valor_min=valor_min,
        valor_max=valor_max,
        only_open=False,
        days_back=days_back,
        max_pages=max_pages,
        page_size=PNCP_PAGE_SIZE,
        limit=limit,
    )
    payload_open = fetch_live_notices(
        endpoint='proposta',
        query=termo,
        uf=uf,
        municipio=municipio,
        modalidade_codigo=modalidade,
        valor_min=valor_min,
        valor_max=valor_max,
        only_open=only_open,
        days_back=days_back,
        max_pages=max_pages,
        page_size=PNCP_PAGE_SIZE,
        limit=limit,
    )
    merged = merge_endpoints(payload_open, payload_pub if not only_open else {'rows': [], 'errors': []}, sort_by=sort_by, limit=limit)

rows = merged['rows']
st.caption(format_query_summary(termo, uf, municipio, only_open, days_back))
st.caption(f'{len(rows)} oportunidade(s) encontrada(s).')

if rows:
    df = build_export_dataframe(rows)
    st.download_button('Baixar CSV do resultado atual', data=df.to_csv(index=False).encode('utf-8-sig'), file_name='busca_suprema_live.csv', mime='text/csv')
    for row in rows:
        opportunity_card(row)
else:
    st.info('Nenhum item retornado para os filtros atuais.')

if merged['errors']:
    with st.expander('Avisos da consulta'):
        for err in merged['errors'][:15]:
            st.warning(err)
