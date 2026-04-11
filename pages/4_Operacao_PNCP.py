from __future__ import annotations

import streamlit as st

from app.core.config import PNCP_MAX_PAGES_PER_QUERY, PNCP_PAGE_SIZE
from app.core.database import Database
from app.services.sync_job import enrich_pending_details, probe_pncp_connection, sync_open_proposals, sync_publications, sync_quick
from app.ui import hero, rows_to_df, set_page

set_page('Operação Live')
db = Database()
stats = db.stats()
hero('Operação Live', 'Alimentação real da base local. A coleta conversa com a API pública do PNCP em segundo plano; a busca do usuário acontece em cima da sua base indexada.')

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric('Itens na base', f"{stats['total']:,}".replace(',', '.'))
with c2:
    st.metric('Propostas abertas', f"{stats['open_now']:,}".replace(',', '.'))
with c3:
    st.metric('Pendentes de detalhe', f"{stats['pending_details']:,}".replace(',', '.'))
with c4:
    st.metric('Detalhes completos', f"{stats['detailed']:,}".replace(',', '.'))

st.markdown('## 1) Teste de conexão')
if st.button('Testar acesso à API pública do PNCP', use_container_width=True):
    with st.spinner('Testando comunicação...'):
        result = probe_pncp_connection()
    if result['ok']:
        st.success(f"{result['message']} · tempo={result['elapsed_seconds']}s")
    else:
        st.error(f"Falha de conexão: {result['message']} · tempo={result['elapsed_seconds']}s")

st.markdown('## 2) Sincronização')
left, right = st.columns(2)
with left:
    if st.button('Sincronização rápida (publicações + propostas abertas)', use_container_width=True):
        with st.spinner('Atualizando base local...'):
            result = sync_quick()
        st.success('Sincronização rápida concluída.')
        st.json(result)
with right:
    if st.button('Enriquecer detalhes pendentes', use_container_width=True):
        with st.spinner('Buscando detalhes das compras...'):
            result = enrich_pending_details()
        st.success('Enriquecimento concluído.')
        st.json(result)

with st.expander('Sincronização avançada'):
    pages = st.slider('Máximo de páginas por modalidade', 1, 30, min(8, PNCP_MAX_PAGES_PER_QUERY))
    page_size = st.selectbox('Tamanho da página', [10, 20, 50, 100], index=1 if PNCP_PAGE_SIZE == 20 else 0)
    c1, c2 = st.columns(2)
    with c1:
        if st.button('Rodar publicações recentes', use_container_width=True):
            with st.spinner('Sincronizando publicações...'):
                result = sync_publications(max_pages=pages, page_size=page_size)
            st.json(result)
    with c2:
        if st.button('Rodar propostas abertas', use_container_width=True):
            with st.spinner('Sincronizando propostas abertas...'):
                result = sync_open_proposals(max_pages=max(2, min(4, pages)), page_size=page_size)
            st.json(result)

st.markdown('## 3) Exportação e histórico')
rows = db.export_rows(
    """
    SELECT numero_controle_pncp, resumo_objeto, orgao_razao_social, municipio_nome, uf_sigla,
           modalidade_nome, data_encerramento_proposta, valor_total_estimado, oportunidade_score, detail_status, is_open_proposal
    FROM opportunities
    ORDER BY updated_at DESC
    LIMIT 1000
    """
)
if rows:
    df = rows_to_df(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button('Baixar CSV da base visível', data=df.to_csv(index=False).encode('utf-8-sig'), file_name='radar_suprema_live.csv', mime='text/csv')
else:
    st.info('Sem registros ainda.')

runs = db.recent_sync_runs(limit=30)
if runs:
    st.markdown('### Histórico operacional')
    st.dataframe(rows_to_df(runs), use_container_width=True, hide_index=True)
