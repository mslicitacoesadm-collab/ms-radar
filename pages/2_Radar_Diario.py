from __future__ import annotations

import streamlit as st

from app.core.database import query_df
from app.core.search_engine import apply_scoring
from app.ui import inject_css, result_card

st.set_page_config(page_title='Radar Diário', page_icon='📡', layout='wide')
inject_css()

st.title('📡 Radar Diário')
st.caption('Tela operacional para acompanhar o que merece atenção imediata.')

base = query_df('SELECT * FROM notices ORDER BY publication_date DESC, estimated_value DESC')
if base.empty:
    st.warning('A base está vazia.')
    st.stop()

query = st.text_input('Perfil do dia', value='material gráfico combustível merenda limpeza engenharia software')
scored = apply_scoring(base, query)

aba1, aba2, aba3 = st.tabs(['Urgentes', 'Maior valor', 'Melhor aderência'])
with aba1:
    urgent = scored.sort_values(['urgency_score', 'opportunity_score'], ascending=[False, False]).head(10)
    for _, row in urgent.iterrows():
        result_card(row)
with aba2:
    high = scored.sort_values('estimated_value', ascending=False).head(10)
    for _, row in high.iterrows():
        result_card(row)
with aba3:
    fit = scored.sort_values(['fit_score', 'opportunity_score'], ascending=[False, False]).head(10)
    for _, row in fit.iterrows():
        result_card(row)
