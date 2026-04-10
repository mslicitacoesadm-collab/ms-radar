from __future__ import annotations

import io
import pandas as pd
import streamlit as st

from app.core.database import Database
from app.services.sync_job import sync_open_opportunities
from app.ui import hero, rows_to_df, set_page

set_page('Operação PNCP')
db = Database()
hero('Operação PNCP', 'Sincronização real da base e controle operacional do coletor.')

with st.form('sync_form'):
    c1, c2, c3 = st.columns(3)
    with c1:
        days_ahead = st.slider('Janela de dias à frente', 0, 10, 3)
    with c2:
        max_pages = st.slider('Máximo de páginas por janela', 1, 100, 20)
    with c3:
        page_size = st.selectbox('Tamanho da página', [10, 20, 50], index=2)
    with_details = st.toggle('Enriquecer com detalhe da contratação', value=True)
    submitted = st.form_submit_button('Sincronizar agora')

if submitted:
    with st.spinner('Sincronizando base real do PNCP...'):
        try:
            result = sync_open_opportunities(days_ahead=days_ahead, max_pages=max_pages, page_size=page_size, with_details=with_details)
            st.success(f"Sincronização concluída. Vistos: {result['seen']} · importados: {result['imported']} · atualizados: {result['updated']}")
        except Exception as exc:
            st.error(f'Falha ao sincronizar o PNCP: {exc}')

st.markdown('## Exportação rápida')
rows = db.export_rows(
    """
    SELECT numero_controle_pncp, resumo_objeto, orgao_razao_social, municipio_nome, uf_sigla,
           modalidade_nome, data_encerramento_proposta, valor_total_estimado, oportunidade_score
    FROM opportunities
    ORDER BY oportunidade_score DESC, data_encerramento_proposta ASC
    LIMIT 1000
    """
)
if rows:
    df = rows_to_df(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    csv_bytes = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button('Baixar CSV da base visível', data=csv_bytes, file_name='radar_suprema_oportunidades.csv', mime='text/csv')
else:
    st.info('Sem registros na base ainda.')

st.markdown('## Histórico de sincronização')
run_rows = db.recent_sync_runs(limit=30)
if run_rows:
    run_df = rows_to_df(run_rows)
    st.dataframe(run_df, use_container_width=True, hide_index=True)
