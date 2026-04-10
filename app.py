from __future__ import annotations

from app.core.database import Database
from app.ui import hero, kpi, set_page
import streamlit as st

set_page('Radar Suprema')
db = Database()
stats = db.stats()

hero(
    'Radar Suprema de Licitações',
    'Busca rápida sobre base própria do PNCP, com coleta resumida e enriquecimento separado para reduzir timeout e melhorar a usabilidade.',
)

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
    kpi('Última atualização', (stats['latest'] or '—')[:16].replace('T', ' '), 'Controle do coletor')

st.markdown('### Fluxo ideal de uso')
left, right = st.columns(2)
with left:
    st.markdown(
        '''
        1. Em **Operação PNCP**, valide a conexão.
        2. Rode **Coleta resumida** para alimentar a base com rapidez.
        3. Rode **Enriquecimento de detalhes** em lotes menores.
        4. Use **Busca Suprema**, **Radar 360** e **Alertas** sem depender do PNCP na tela.
        '''
    )
with right:
    st.info(
        'O sistema foi ajustado para evitar o erro clássico de timeout: primeiro salva os resumos, depois busca os detalhes em segunda etapa.'
    )

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
