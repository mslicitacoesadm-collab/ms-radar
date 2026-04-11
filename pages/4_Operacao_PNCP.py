from __future__ import annotations

import streamlit as st

from app.core.config import PNCP_CACHE_TTL_SECONDS, PNCP_DEFAULT_DAYS_BACK, PNCP_MAX_PAGES_PER_QUERY, PNCP_PAGE_SIZE
from app.core.live_service import build_export_dataframe, fetch_live_notices, merge_endpoints, probe_connection_cached
from app.ui import connection_banner, hero, set_page

set_page('Operação PNCP Live')
hero('Operação PNCP Live', 'Painel técnico do modo espelho. O sistema já entra consultando o PNCP, sem botão de start e sem base local.')

if st.button('Atualizar leitura agora', use_container_width=True):
    st.cache_data.clear()
    st.rerun()

probe = probe_connection_cached()
connection_banner(probe['ok'], probe['message'], probe['elapsed_seconds'])

if not probe['ok']:
    st.error('Sem comunicação com a API pública do PNCP neste momento.')
    st.stop()

with st.spinner('Executando leitura técnica ao vivo...'):
    payload_pub = fetch_live_notices(endpoint='publicacao', days_back=PNCP_DEFAULT_DAYS_BACK, max_pages=PNCP_MAX_PAGES_PER_QUERY, page_size=PNCP_PAGE_SIZE, limit=50)
    payload_open = fetch_live_notices(endpoint='proposta', only_open=True, days_back=PNCP_DEFAULT_DAYS_BACK, max_pages=max(1, min(3, PNCP_MAX_PAGES_PER_QUERY)), page_size=PNCP_PAGE_SIZE, limit=50)
    merged = merge_endpoints(payload_open, payload_pub, sort_by='score', limit=50)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric('Consultas cacheadas', f'{PNCP_CACHE_TTL_SECONDS}s')
with c2:
    st.metric('Dias consultados', f'{PNCP_DEFAULT_DAYS_BACK}')
with c3:
    st.metric('Páginas máximas', f'{PNCP_MAX_PAGES_PER_QUERY}')
with c4:
    st.metric('Itens retornados', f"{merged['count']}")

st.markdown('### Resultado técnico da leitura atual')
df = build_export_dataframe(merged['rows'])
if not df.empty:
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.download_button('Baixar CSV da leitura atual', data=df.to_csv(index=False).encode('utf-8-sig'), file_name='operacao_pncp_live.csv', mime='text/csv')
else:
    st.info('Nenhum registro foi retornado nesta leitura.')

if payload_pub['errors'] or payload_open['errors']:
    st.markdown('### Avisos técnicos')
    for err in (payload_pub['errors'] + payload_open['errors'])[:20]:
        st.warning(err)
