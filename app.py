from __future__ import annotations

import streamlit as st

from app.core.config import PNCP_DEFAULT_DAYS_BACK, PNCP_HOME_LIMIT
from app.core.live_service import compute_dashboard_metrics, fetch_live_notices, merge_endpoints, probe_connection_cached
from app.core.utils import money
from app.ui import connection_banner, hero, kpi, opportunity_card, set_page

set_page('Radar Espelho PNCP')

hero(
    'Radar Espelho PNCP',
    'Consulta viva no PNCP, sem banco local e sem sincronização manual. Ao entrar, o sistema já testa a conexão e carrega oportunidades em tempo real.',
)

probe = probe_connection_cached()
connection_banner(probe['ok'], probe['message'], probe['elapsed_seconds'])

if not probe['ok']:
    st.error('A conexão com o PNCP falhou neste momento. O sistema permanece em modo espelho e depende da resposta ao vivo da API pública.')
    st.stop()

with st.spinner('Conectando ao PNCP e carregando o painel inicial...'):
    payload_pub = fetch_live_notices(endpoint='publicacao', days_back=PNCP_DEFAULT_DAYS_BACK, limit=PNCP_HOME_LIMIT, max_pages=2, page_size=20)
    payload_open = fetch_live_notices(endpoint='proposta', days_back=PNCP_DEFAULT_DAYS_BACK, only_open=True, limit=PNCP_HOME_LIMIT, max_pages=2, page_size=20)
    merged = merge_endpoints(payload_open, payload_pub, sort_by='score', limit=PNCP_HOME_LIMIT)

rows = merged['rows']
metrics = compute_dashboard_metrics(rows)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    kpi('Resultados live', f"{metrics['total']}", 'Consulta atual sem armazenamento')
with c2:
    kpi('Propostas abertas', f"{metrics['open_now']}", 'Com recebimento em andamento')
with c3:
    kpi('Urgentes 48h', f"{metrics['urgent']}", 'Priorização imediata')
with c4:
    kpi('Valor estimado', money(metrics['valor_total']), 'Soma da leitura atual')
with c5:
    kpi('UF líder', metrics['top_uf'], metrics['top_modalidade'])

left, right = st.columns([1.2, 1])
with left:
    st.markdown('### Como funciona agora')
    st.markdown(
        '''
        1. **Ao abrir o site**, o app valida a API pública do PNCP.
        2. **A busca é imediata**, sem depender de banco local.
        3. **O painel classifica** urgência, valor e aderência comercial.
        4. **Cada atualização da tela** consulta o PNCP novamente, com cache curto para evitar excesso de chamadas.
        '''
    )
with right:
    st.info(
        'Este projeto está em **modo espelho**. Isso significa:\n\n'
        '- sem SQLite\n'
        '- sem sincronização manual\n'
        '- sem histórico persistente\n'
        '- sem armazenamento de licitações\n\n'
        'A informação exibida pertence apenas à consulta atual.'
    )

if merged['errors']:
    with st.expander('Avisos da consulta atual'):
        for err in merged['errors'][:12]:
            st.warning(err)

st.markdown('### Oportunidades carregadas ao entrar')
if rows:
    for row in rows[:12]:
        opportunity_card(row)
else:
    st.info('Nenhuma oportunidade foi retornada nesta leitura inicial. Ajuste os filtros nas páginas laterais para ampliar a busca.')
