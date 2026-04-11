from __future__ import annotations

import streamlit as st

from app.core.database import Database
from app.ui import hero, kpi, set_page

set_page('Radar Suprema Live')
db = Database()
stats = db.stats()
last_pub = db.get_state('last_publication_sync', '—')
last_open = db.get_state('last_open_sync', '—')

hero(
    'Radar Suprema Live',
    'Sistema de busca e alerta de licitações com base própria. O usuário pesquisa na sua base local já sincronizada do PNCP, sem depender da resposta ao vivo do portal na hora da busca.',
)

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    kpi('Base indexada', f"{stats['total']:,}".replace(',', '.'), 'Licitações gravadas na base local')
with c2:
    kpi('Propostas abertas', f"{stats['open_now']:,}".replace(',', '.'), 'Com recebimento em andamento')
with c3:
    kpi('Urgentes 48h', f"{stats['urgent']:,}".replace(',', '.'), 'Priorização imediata')
with c4:
    kpi('Detalhes pendentes', f"{stats['pending_details']:,}".replace(',', '.'), 'Itens a enriquecer')
with c5:
    kpi('Detalhes completos', f"{stats['detailed']:,}".replace(',', '.'), 'Itens já enriquecidos')

left, right = st.columns([1.2, 1])
with left:
    st.markdown('### Fluxo operacional ideal')
    st.markdown(
        '''
        1. **GitHub Actions** alimenta a base automaticamente.
        2. **Busca Suprema** pesquisa localmente, sem timeout na tela do usuário.
        3. **Radar Diário** mostra o que vale a pena agir agora.
        4. **Alertas Inteligentes** transformam nichos e regiões em monitoramento contínuo.
        '''
    )
with right:
    st.info(f'Última sincronização de publicações: **{last_pub}**\n\nÚltima verificação de propostas abertas: **{last_open}**')

runs = db.recent_sync_runs(limit=10)
st.markdown('### Histórico recente')
if runs:
    for run in runs:
        st.write(f"**#{run['id']}** · {run['source']} · {run['status']} · vistos={run['total_seen']} · importados={run['total_imported']} · atualizados={run['total_updated']}")
        if run['details']:
            st.caption(run['details'])
else:
    st.warning('Ainda não há sincronizações registradas. Vá em Operação Live e rode a primeira coleta.')
