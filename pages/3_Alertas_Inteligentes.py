from __future__ import annotations

import streamlit as st

from app.core.alerts import evaluate_alerts
from app.core.config import MODALIDADES
from app.core.database import Database
from app.ui import hero, set_page

set_page('Alertas Inteligentes')
db = Database()
hero('Alertas Inteligentes', 'Cadastre nichos, regiões e filtros. O sistema cruza isso com a base local e mostra correspondências reais.')

ufs = [''] + db.distinct_values('uf_sigla') if db.stats()['total'] else ['']
municipios = [''] + db.distinct_values('municipio_nome') if db.stats()['total'] else ['']

with st.form('alert_form'):
    c1, c2 = st.columns(2)
    with c1:
        nome = st.text_input('Nome do alerta', placeholder='Ex.: Combustível Bahia')
        termos = st.text_input('Termos-chave', placeholder='combustível, diesel, gasolina')
        uf = st.selectbox('UF', ufs)
        municipio = st.selectbox('Município', municipios)
    with c2:
        modalidade = st.selectbox('Modalidade', options=[0] + list(MODALIDADES.keys()), format_func=lambda x: 'Todas' if x == 0 else MODALIDADES[x])
        valor_min = st.number_input('Valor mínimo', min_value=0.0, value=0.0, step=1000.0)
        valor_max = st.number_input('Valor máximo', min_value=0.0, value=0.0, step=1000.0)
        email = st.text_input('E-mail para aviso (opcional)')
        somente_abertas = st.toggle('Somente abertas', value=True)
    submitted = st.form_submit_button('Salvar alerta')

if submitted:
    if not nome.strip() or not termos.strip():
        st.error('Informe nome e termos-chave.')
    else:
        db.save_alert_profile(
            {
                'nome': nome.strip(),
                'termos': termos.strip(),
                'uf_sigla': uf or None,
                'municipio_nome': municipio or None,
                'modalidade_codigo': None if modalidade == 0 else modalidade,
                'valor_min': valor_min if valor_min > 0 else None,
                'valor_max': valor_max if valor_max > 0 else None,
                'somente_abertas': somente_abertas,
                'canal_email': email.strip() or None,
            }
        )
        st.success('Alerta salvo.')

st.markdown('### Alertas ativos')
for alert in db.list_alert_profiles():
    st.write(f"**#{alert['id']} · {alert['nome']}** — {alert['termos']}")
    st.caption(f"UF: {alert['uf_sigla'] or 'todas'} · Município: {alert['municipio_nome'] or 'todos'} · Modalidade: {alert['modalidade_codigo'] or 'todas'}")

st.markdown('### Prévia de correspondências')
report = evaluate_alerts()
for item in report['alerts']:
    alerta = item['alerta']
    st.write(f"**{alerta['nome']}** — {item['total_matches']} oportunidade(s)")
    for match in item['matches'][:5]:
        st.caption(f"{match['municipio_nome']}/{match['uf_sigla']} · {match['modalidade_nome']} · {match['resumo_objeto']}")
