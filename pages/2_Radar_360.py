from __future__ import annotations

import streamlit as st

from app.core.config import NICHOS_PRONTOS
from app.core.database import Database
from app.ui import hero, opportunity_card, set_page

set_page('Radar Diário')
db = Database()
stats = db.stats()
hero('Radar Diário', 'Visão pronta para ação: urgência, maior valor, propostas abertas e nichos que mais importam para quem vive de licitação.')

if stats['total'] == 0:
    st.warning('Ainda não há base local alimentada.')
    st.stop()

c1, c2 = st.columns(2)
with c1:
    st.markdown('### Propostas abertas mais fortes')
    rows = db.export_rows(
        """
        SELECT * FROM opportunities
        WHERE is_open_proposal = 1 AND date(COALESCE(data_encerramento_proposta,'')) >= date('now')
        ORDER BY oportunidade_score DESC, data_encerramento_proposta ASC
        LIMIT 8
        """
    )
    for row in rows:
        opportunity_card(dict(row))
with c2:
    st.markdown('### Maior potencial financeiro')
    rows = db.export_rows(
        """
        SELECT * FROM opportunities
        WHERE COALESCE(valor_total_estimado, 0) > 0
        ORDER BY valor_total_estimado DESC, oportunidade_score DESC
        LIMIT 8
        """
    )
    for row in rows:
        opportunity_card(dict(row))

st.markdown('### Radar por nicho')
cols = st.columns(4)
for idx, (nicho, termos) in enumerate(NICHOS_PRONTOS.items()):
    query = ' '.join(termos[:3])
    total = len(db.search_opportunities(query=query, only_open=True, limit=20))
    with cols[idx % 4]:
        st.metric(nicho, total)
