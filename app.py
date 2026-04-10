from __future__ import annotations

import streamlit as st

from app.core.config import SETTINGS
from app.core.database import ensure_database, insert_sync_history, query_df, upsert_notices
from app.core.pncp_client import fetch_open_notices, load_demo_notices
from app.ui import hero, inject_css, metric_card


st.set_page_config(
    page_title='Radar Licita Pro',
    page_icon='📡',
    layout='wide',
    initial_sidebar_state='expanded',
)

inject_css()
ensure_database()

st.sidebar.title('Radar Licita Pro')
st.sidebar.caption('Busca inteligente, radar diário e centro de alertas.')
with st.sidebar.expander('Status da operação', expanded=True):
    st.write(f"**PNCP:** {'configurado' if SETTINGS.pncp_base_url else 'não configurado'}")
    st.write(f"**Alertas:** {'prontos' if SETTINGS.alerts_ready else 'pendentes'}")
    st.write(f"**Base local:** SQLite ativa")

hero(
    'Radar Licita Pro',
    'Plataforma profissional para quem precisa encontrar oportunidades com rapidez, enxergar prioridade comercial e estruturar alertas sem atrito.',
    badges=['Busca simples', 'Ranking comercial', 'PNCP integrado', 'Alertas prontos para operação'],
)

col1, col2 = st.columns([1.6, 1], gap='large')
with col1:
    st.markdown('### Comece em 1 clique')
    st.write('Use o modo mais simples para alimentar a base agora mesmo. Depois, vá para a página **Busca Inteligente** para trabalhar como usuário final.')
    c1, c2, c3 = st.columns(3)
    if c1.button('Carregar base demo', use_container_width=True):
        notices = load_demo_notices()
        total = upsert_notices(notices)
        insert_sync_history('demo', total, 'ok', 'Carga manual pela interface')
        st.success(f'Base demo carregada com {total} oportunidades.')
    if c2.button('Sincronizar PNCP agora', use_container_width=True):
        try:
            notices = fetch_open_notices(days_ahead=30)
            total = upsert_notices(notices)
            insert_sync_history('pncp', total, 'ok', 'Sincronização manual pela interface')
            st.success(f'Sincronização concluída com {total} oportunidades.')
        except Exception as exc:
            st.error(f'Falha ao sincronizar o PNCP: {exc}')
    if c3.button('Atualizar status', use_container_width=True):
        st.rerun()

    st.markdown('### Visão executiva')
    metrics = query_df(
        '''
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(estimated_value),0) AS valor,
            COUNT(DISTINCT state) AS ufs,
            COUNT(DISTINCT city) AS cidades
        FROM notices
        '''
    ).iloc[0]

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        metric_card('Oportunidades na base', f"{int(metrics['total'])}", 'Leituras prontas para busca e alerta.')
    with m2:
        metric_card('Valor potencial', f"R$ {float(metrics['valor']):,.0f}".replace(',', '.'), 'Soma bruta estimada encontrada.')
    with m3:
        metric_card('UFs cobertas', f"{int(metrics['ufs'])}", 'Cobertura já presente no banco local.')
    with m4:
        metric_card('Municípios', f"{int(metrics['cidades'])}", 'Capilaridade operacional da base.')

with col2:
    st.markdown('### Fluxo ideal de uso')
    st.info('1. Alimente a base.\n2. Busque por palavra ou objeto.\n3. Salve alertas.\n4. Acompanhe o radar diário.\n5. Exporte o que interessa.')
    st.markdown('### O que torna esta versão mais profissional')
    st.write(
        '- interface pensada para uso rápido\n'
        '- foco em priorização comercial\n'
        '- visão por prazo, valor e aderência\n'
        '- cadastro de alertas direto pela tela\n'
        '- base pronta para evolução jurídica'
    )

st.markdown('### Últimas sincronizações')
history = query_df('SELECT created_at, origin, total_imported, status, details FROM sync_history ORDER BY id DESC LIMIT 8')
if history.empty:
    st.caption('Nenhuma sincronização registrada ainda.')
else:
    st.dataframe(history, use_container_width=True, hide_index=True)
