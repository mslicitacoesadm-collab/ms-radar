from __future__ import annotations

import streamlit as st

from app.core.config import MODALIDADES
from app.core.database import Database
from app.ui import hero, opportunity_card, set_page

set_page('Busca Suprema')
db = Database()
stats = db.stats()
hero('Busca Suprema', 'Busca profissional em base local indexada. Rápida para o usuário, sem depender do tempo de resposta do PNCP na hora da pesquisa.')

if stats['total'] == 0:
    st.warning('A base ainda está vazia. Vá para Operação Live e execute a sincronização.')
    st.stop()

ufs = [''] + db.distinct_values('uf_sigla')
municipios = [''] + db.distinct_values('municipio_nome')

c1, c2, c3, c4 = st.columns([3.4, 1.1, 2.2, 1.4])
with c1:
    termo = st.text_input('Busca por objeto, nicho ou palavra-chave', placeholder='Ex.: material gráfico, combustível, merenda, software')
with c2:
    uf = st.selectbox('UF', ufs)
with c3:
    municipio = st.selectbox('Município', municipios)
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

limit = st.select_slider('Quantidade de resultados', options=[20, 50, 100, 200], value=50)

rows = db.search_opportunities(
    query=termo,
    uf=uf,
    municipio=municipio,
    modalidade_codigo=None if modalidade == 0 else modalidade,
    only_open=only_open,
    valor_min=valor_min,
    valor_max=valor_max,
    sort_by=sort_by,
    limit=limit,
)

st.caption(f'{len(rows)} oportunidade(s) encontrada(s).')
for row in rows:
    opportunity_card(dict(row))
