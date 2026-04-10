from __future__ import annotations

import json

import pandas as pd
import streamlit as st

from app.core.database import query_df, save_view
from app.core.search_engine import apply_scoring
from app.ui import format_brl, inject_css, result_card

st.set_page_config(page_title='Busca Inteligente', page_icon='🔎', layout='wide')
inject_css()

st.title('🔎 Busca Inteligente')
st.caption('Uma tela pensada para quem quer encontrar rápido, filtrar fácil e decidir sem perder tempo.')

base = query_df('SELECT * FROM notices ORDER BY publication_date DESC, estimated_value DESC')
if base.empty:
    st.warning('A base está vazia. Volte para a página inicial e carregue a base demo ou sincronize o PNCP.')
    st.stop()

with st.sidebar:
    st.subheader('Filtros')
    query = st.text_input('Busca livre', placeholder='Ex.: material gráfico, combustível, merenda, software...')
    state = st.selectbox('UF', ['Todas'] + sorted([s for s in base['state'].dropna().unique().tolist() if s]))
    city = st.selectbox('Município', ['Todos'] + sorted([s for s in base['city'].dropna().unique().tolist() if s]))
    modality = st.selectbox('Modalidade', ['Todas'] + sorted([s for s in base['modality'].dropna().unique().tolist() if s]))
    min_value = st.number_input('Valor mínimo estimado', min_value=0.0, value=0.0, step=5000.0)
    order = st.selectbox('Ordenar por', ['Oportunidade', 'Valor estimado', 'Prazo', 'Publicação'])
    save_name = st.text_input('Salvar esta visão como')
    if st.button('Salvar visão', use_container_width=True) and save_name.strip():
        save_view(save_name.strip(), json.dumps({'query': query, 'state': state, 'city': city, 'modality': modality, 'min_value': min_value}, ensure_ascii=False))
        st.success('Visão salva com sucesso.')

filtered = base.copy()
if state != 'Todas':
    filtered = filtered[filtered['state'] == state]
if city != 'Todos':
    filtered = filtered[filtered['city'] == city]
if modality != 'Todas':
    filtered = filtered[filtered['modality'] == modality]
if min_value > 0:
    filtered = filtered[filtered['estimated_value'].fillna(0) >= min_value]

scored = apply_scoring(filtered, query or '')
if order == 'Valor estimado':
    scored = scored.sort_values('estimated_value', ascending=False)
elif order == 'Prazo':
    scored = scored.sort_values('deadline_date', ascending=True)
elif order == 'Publicação':
    scored = scored.sort_values('publication_date', ascending=False)

c1, c2, c3, c4 = st.columns(4)
c1.metric('Resultados', len(scored))
c2.metric('Maior oportunidade', f"{scored['opportunity_score'].max():.1f}" if not scored.empty else '0')
c3.metric('Valor médio', format_brl(scored['estimated_value'].fillna(0).mean() if not scored.empty else 0))
c4.metric('Prazo mais próximo', scored['deadline_date'].min() if not scored.empty else '-')

st.markdown('### Resultados priorizados')
show = scored.head(50)
for _, row in show.iterrows():
    result_card(row)
    exp1, exp2, exp3 = st.columns([1.2, 1, 1])
    with exp1:
        st.link_button('Abrir origem', row.get('source_url') or 'https://pncp.gov.br', use_container_width=True)
    with exp2:
        st.download_button(
            'Baixar resumo JSON',
            data=json.dumps(row.to_dict(), ensure_ascii=False, indent=2),
            file_name=f"{row.get('source_id','oportunidade')}.json",
            mime='application/json',
            use_container_width=True,
            key=f"json_{row.get('source_id')}"
        )
    with exp3:
        texto = f"{row.get('title')} | {row.get('agency')} | {row.get('city')}/{row.get('state')} | prazo {row.get('deadline_date')} | valor {format_brl(row.get('estimated_value',0))}"
        st.code(texto, language=None)
