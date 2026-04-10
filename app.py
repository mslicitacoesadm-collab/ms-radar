from __future__ import annotations

from app.core.database import Database
from app.ui import hero, kpi, set_page
import streamlit as st


set_page('Radar Suprema')
db = Database()
stats = db.stats()

hero(
    'Radar Suprema de Licitações',
    'Busca real sobre base própria sincronizada do PNCP. Menos ruído, mais oportunidade pronta para decisão.',
)

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi('Oportunidades na base', f"{stats['total']:,}".replace(',', '.'), 'Base indexada para busca instantânea')
with c2:
    kpi('Em prazo aberto', f"{stats['open_now']:,}".replace(',', '.'), 'Contratações ainda utilizáveis')
with c3:
    kpi('Encerram em 48h', f"{stats['urgent']:,}".replace(',', '.'), 'Radar de urgência para ação rápida')
with c4:
    kpi('Última atualização', (stats['latest'] or '—')[:16].replace('T', ' '), 'Controle operacional do coletor')

st.markdown('### Como operar')
left, right = st.columns(2)
with left:
    st.markdown(
        '''
        1. Abra **Operação PNCP** e sincronize uma janela curta.
        2. Use **Busca Suprema** para pesquisar por objeto, órgão, UF e município.
        3. Salve perfis em **Alertas** para transformar busca em rotina.
        '''
    )
with right:
    st.info(
        'Esta versão não consulta o PNCP na tela de busca. Primeiro sincroniza, depois entrega pesquisa rápida e profissional.'
    )

runs = db.recent_sync_runs(limit=8)
st.markdown('### Últimas sincronizações')
if runs:
    for run in runs:
        st.write(
            f"**#{run['id']}** · {run['status']} · {run['started_at'][:16].replace('T', ' ')} · vistos={run['total_seen']} · importados={run['total_imported']} · atualizados={run['total_updated']}"
        )
        if run['details']:
            st.caption(run['details'])
else:
    st.warning('Nenhuma sincronização executada ainda. Vá para Operação PNCP para alimentar a base com dados reais.')
