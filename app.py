from __future__ import annotations

from app.core.config import PNCP_SOURCE_MODE
from app.core.database import Database
from app.ui import hero, kpi, set_page
import streamlit as st

set_page('Radar Suprema')
db = Database()
stats = db.stats()

hero('Radar Suprema de Licitações', 'Produto profissional com coleta híbrida do PNCP, base própria rápida e experiência pensada para quem trabalha no dia a dia com licitações.')

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    kpi('Base indexada', f"{stats['total']:,}".replace(',', '.'), 'Oportunidades salvas localmente')
with c2:
    kpi('Prazo aberto', f"{stats['open_now']:,}".replace(',', '.'), 'Contratações utilizáveis agora')
with c3:
    kpi('Urgentes 48h', f"{stats['urgent']:,}".replace(',', '.'), 'Janela de ação rápida')
with c4:
    kpi('Detalhes pendentes', f"{stats['pending_details']:,}".replace(',', '.'), 'Itens prontos para enriquecimento')
with c5:
    kpi('Fonte ativa', PNCP_SOURCE_MODE.upper(), 'API, scraping ou híbrido')

st.markdown('### Como o sistema trabalha')
left, right = st.columns(2)
with left:
    st.markdown(
        '''
        1. Em **Operação PNCP**, rode o teste de conexão.
        2. Alimente a base com a **sincronização real**.
        3. Enriqueça os detalhes pendentes em lotes menores.
        4. Pesquise sem travar a tela do usuário.
        '''
    )
with right:
    st.info('Agora o teste respeita o mínimo de 10 itens por página e a coleta pode usar scraping público quando a API oficial estiver lenta.')

runs = db.recent_sync_runs(limit=8)
st.markdown('### Últimas sincronizações')
if runs:
    for run in runs:
        st.write(
            f"**#{run['id']}** · {run['source']} · {run['status']} · {run['started_at'][:16].replace('T', ' ')} · vistos={run['total_seen']} · importados={run['total_imported']} · atualizados={run['total_updated']}"
        )
        if run['details']:
            st.caption(run['details'])
else:
    st.warning('Nenhuma sincronização executada ainda. Vá para Operação PNCP para testar conexão e alimentar a base.')
