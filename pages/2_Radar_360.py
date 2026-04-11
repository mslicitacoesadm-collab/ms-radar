from __future__ import annotations

import streamlit as st

from app.core.config import NICHOS_PRONTOS, PNCP_DEFAULT_DAYS_BACK
from app.core.live_service import fetch_live_notices, probe_connection_cached
from app.core.search_engine import expand_query
from app.ui import connection_banner, hero, opportunity_card, set_page

set_page('Radar 360 Live')
hero('Radar 360 Live', 'Leitura tática do PNCP ao vivo: propostas abertas, maior potencial financeiro e radar por nicho sem armazenamento local.')

probe = probe_connection_cached()
connection_banner(probe['ok'], probe['message'], probe['elapsed_seconds'])
if not probe['ok']:
    st.stop()

with st.spinner('Montando o radar ao vivo...'):
    open_rows = fetch_live_notices(endpoint='proposta', only_open=True, days_back=PNCP_DEFAULT_DAYS_BACK, max_pages=2, page_size=20, limit=24)['rows']
    high_value_rows = fetch_live_notices(endpoint='publicacao', days_back=PNCP_DEFAULT_DAYS_BACK, max_pages=2, page_size=20, limit=40)['rows']
    high_value_rows = sorted(high_value_rows, key=lambda r: (-float(r.get('valor_total_estimado') or 0), -float(r.get('oportunidade_score') or 0)))[:8]

c1, c2 = st.columns(2)
with c1:
    st.markdown('### Propostas abertas mais fortes')
    for row in open_rows[:8]:
        opportunity_card(row)
with c2:
    st.markdown('### Maior potencial financeiro')
    for row in high_value_rows:
        opportunity_card(row)

st.markdown('### Radar por nicho')
cols = st.columns(4)
for idx, (nicho, termos) in enumerate(NICHOS_PRONTOS.items()):
    payload = fetch_live_notices(endpoint='publicacao', query=' '.join(termos[:3]), only_open=False, days_back=PNCP_DEFAULT_DAYS_BACK, max_pages=1, page_size=20, limit=20)
    with cols[idx % 4]:
        st.metric(nicho, payload['count'])
        st.caption(', '.join(termos[:3]))
