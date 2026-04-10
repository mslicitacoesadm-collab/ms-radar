from __future__ import annotations

import streamlit as st

from app.core.database import Database
from app.ui import hero, opportunity_card, set_page

set_page('Radar 360')
db = Database()
hero('Radar 360', 'Leitura executiva para quem precisa abrir o sistema e encontrar prioridade em segundos.')

if db.stats()['total'] == 0:
    st.warning('Ainda não há base local. Sincronize primeiro em Operação PNCP.')
    st.stop()

col1, col2 = st.columns(2)
with col1:
    st.markdown('## Vencem em até 72h')
    urgent = db.export_rows(
        """
        SELECT * FROM opportunities
        WHERE date(data_encerramento_proposta) BETWEEN date('now') AND date('now', '+3 day')
        ORDER BY oportunidade_score DESC, data_encerramento_proposta ASC
        LIMIT 8
        """
    )
    for row in urgent:
        opportunity_card(dict(row))
with col2:
    st.markdown('## Maior potencial financeiro')
    premium = db.export_rows(
        """
        SELECT * FROM opportunities
        WHERE date(data_encerramento_proposta) >= date('now')
        ORDER BY valor_total_estimado DESC, oportunidade_score DESC
        LIMIT 8
        """
    )
    for row in premium:
        opportunity_card(dict(row))
