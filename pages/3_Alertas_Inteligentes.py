from __future__ import annotations

import streamlit as st

from app.core.config import DEFAULT_UFS, MODALIDADES, PNCP_DEFAULT_DAYS_BACK
from app.core.live_service import fetch_live_notices, merge_endpoints, probe_connection_cached
from app.ui import connection_banner, hero, set_page

set_page('Alertas Inteligentes')
hero('Alertas Inteligentes', 'Monte filtros vivos e veja correspondências do PNCP na sessão atual. Nada é salvo em banco; os alertas permanecem apenas enquanto a sessão estiver aberta.')

probe = probe_connection_cached()
connection_banner(probe['ok'], probe['message'], probe['elapsed_seconds'])
if not probe['ok']:
    st.stop()

if 'alert_profiles' not in st.session_state:
    st.session_state.alert_profiles = []

with st.form('alert_form'):
    c1, c2 = st.columns(2)
    with c1:
        nome = st.text_input('Nome do alerta', placeholder='Ex.: Combustível Bahia')
        termos = st.text_input('Termos-chave', placeholder='combustível, diesel, gasolina')
        uf = st.selectbox('UF', DEFAULT_UFS)
        municipio = st.text_input('Município', placeholder='Ex.: Salvador')
    with c2:
        modalidade = st.selectbox('Modalidade', options=[0] + list(MODALIDADES.keys()), format_func=lambda x: 'Todas' if x == 0 else MODALIDADES[x])
        valor_min = st.number_input('Valor mínimo', min_value=0.0, value=0.0, step=1000.0)
        valor_max = st.number_input('Valor máximo', min_value=0.0, value=0.0, step=1000.0)
        somente_abertas = st.toggle('Somente abertas', value=True)
        days_back = st.slider('Janela de dias do alerta', 1, 30, PNCP_DEFAULT_DAYS_BACK)
    submitted = st.form_submit_button('Adicionar alerta na sessão')

if submitted:
    if not nome.strip() or not termos.strip():
        st.error('Informe nome e termos-chave.')
    else:
        st.session_state.alert_profiles.append(
            {
                'nome': nome.strip(),
                'termos': termos.strip(),
                'uf_sigla': uf or '',
                'municipio_nome': municipio.strip(),
                'modalidade_codigo': modalidade,
                'valor_min': valor_min,
                'valor_max': valor_max,
                'somente_abertas': somente_abertas,
                'days_back': days_back,
            }
        )
        st.success('Alerta adicionado à sessão atual.')

st.markdown('### Alertas ativos na sessão')
if st.session_state.alert_profiles:
    for i, alert in enumerate(st.session_state.alert_profiles, start=1):
        st.write(f"**#{i} · {alert['nome']}** — {alert['termos']}")
        st.caption(f"UF: {alert['uf_sigla'] or 'todas'} · Município: {alert['municipio_nome'] or 'todos'} · Modalidade: {alert['modalidade_codigo'] or 'todas'}")
else:
    st.info('Nenhum alerta criado nesta sessão ainda.')

st.markdown('### Prévia de correspondências live')
for alert in st.session_state.alert_profiles:
    payload_pub = fetch_live_notices(
        endpoint='publicacao',
        query=alert['termos'],
        uf=alert['uf_sigla'],
        municipio=alert['municipio_nome'],
        modalidade_codigo=alert['modalidade_codigo'],
        valor_min=alert['valor_min'],
        valor_max=alert['valor_max'],
        only_open=False,
        days_back=alert['days_back'],
        max_pages=2,
        page_size=20,
        limit=10,
    )
    payload_open = fetch_live_notices(
        endpoint='proposta',
        query=alert['termos'],
        uf=alert['uf_sigla'],
        municipio=alert['municipio_nome'],
        modalidade_codigo=alert['modalidade_codigo'],
        valor_min=alert['valor_min'],
        valor_max=alert['valor_max'],
        only_open=alert['somente_abertas'],
        days_back=alert['days_back'],
        max_pages=2,
        page_size=20,
        limit=10,
    )
    merged = merge_endpoints(payload_open, payload_pub if not alert['somente_abertas'] else {'rows': [], 'errors': []}, sort_by='score', limit=10)
    st.write(f"**{alert['nome']}** — {merged['count']} oportunidade(s)")
    for match in merged['rows'][:5]:
        st.caption(f"{match['municipio_nome']}/{match['uf_sigla']} · {match['modalidade_nome']} · {match['resumo_objeto']}")
