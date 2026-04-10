from __future__ import annotations

import streamlit as st

from app.core.config import MODALIDADES
from app.core.database import Database
from app.services.sync_job import enrich_pending_details, probe_pncp_connection, sync_open_summaries
from app.ui import hero, rows_to_df, set_page

set_page('Operação PNCP')
db = Database()
stats = db.stats()
hero('Operação PNCP', 'Coleta enxuta, enriquecimento separado e base própria rápida para busca profissional.')

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric('Itens na base', f"{stats['total']:,}".replace(',', '.'))
with c2:
    st.metric('Detalhes pendentes', f"{stats['pending_details']:,}".replace(',', '.'))
with c3:
    st.metric('Detalhes completos', f"{stats['detailed']:,}".replace(',', '.'))
with c4:
    st.metric('Em prazo aberto', f"{stats['open_now']:,}".replace(',', '.'))

st.markdown('## 1) Teste de conexão')
probe_col1, probe_col2 = st.columns([2, 1])
with probe_col1:
    probe_modalidade = st.selectbox('Modalidade para teste', options=[0] + list(MODALIDADES.keys()), format_func=lambda x: 'Auto' if x == 0 else MODALIDADES[x])
with probe_col2:
    if st.button('Testar conexão com o PNCP', use_container_width=True):
        with st.spinner('Validando conexão...'):
            result = probe_pncp_connection(None if probe_modalidade == 0 else probe_modalidade)
        if result['ok']:
            st.success(f"{result['message']} · tempo={result['elapsed_seconds']}s")
        else:
            st.error(f"Falha de conexão: {result['message']} · tempo={result['elapsed_seconds']}s")

st.markdown('## 2) Coleta resumida')
with st.form('summary_sync_form'):
    s1, s2, s3 = st.columns(3)
    with s1:
        modalidade = st.selectbox('Modalidade', options=[0] + list(MODALIDADES.keys()), format_func=lambda x: 'Auto / todas as necessárias' if x == 0 else MODALIDADES[x])
    with s2:
        max_pages = st.slider('Máximo de páginas', 1, 80, 12)
    with s3:
        page_size = st.selectbox('Tamanho da página', [10, 20, 50], index=1)
    summary_submitted = st.form_submit_button('Sincronizar resumos agora')

if summary_submitted:
    with st.spinner('Sincronizando resumos reais do PNCP...'):
        try:
            result = sync_open_summaries(
                codigo_modalidade=None if modalidade == 0 else modalidade,
                max_pages=max_pages,
                page_size=page_size,
            )
            msg = f"Concluído. vistos={result['seen']} · linhas={result['rows']} · importados={result['imported']} · atualizados={result['updated']}"
            if result['errors']:
                st.warning(msg)
                st.caption('\n'.join(result['errors'][:10]))
            else:
                st.success(msg)
        except Exception as exc:
            st.error(f'Falha ao sincronizar o PNCP: {exc}')

st.markdown('## 3) Enriquecimento de detalhes')
with st.form('detail_sync_form'):
    batch_size = st.slider('Quantidade de itens para enriquecer', 5, 120, 30)
    detail_submitted = st.form_submit_button('Enriquecer detalhes pendentes')

if detail_submitted:
    with st.spinner('Buscando detalhes das contratações...'):
        try:
            result = enrich_pending_details(batch_size=batch_size)
            msg = f"Processados={result['processed']} · sucesso={result['success']} · falhas={result['failed']}"
            if result['failed']:
                st.warning(msg)
                st.caption('\n'.join(result['errors'][:10]))
            else:
                st.success(msg)
        except Exception as exc:
            st.error(f'Falha ao enriquecer detalhes: {exc}')

st.markdown('## 4) Exportação rápida')
rows = db.export_rows(
    """
    SELECT numero_controle_pncp, resumo_objeto, orgao_razao_social, municipio_nome, uf_sigla,
           modalidade_nome, data_encerramento_proposta, valor_total_estimado, oportunidade_score, detail_status
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

st.markdown('## 5) Histórico operacional')
run_rows = db.recent_sync_runs(limit=30)
if run_rows:
    run_df = rows_to_df(run_rows)
    st.dataframe(run_df, use_container_width=True, hide_index=True)
else:
    st.info('Ainda não há histórico.')
