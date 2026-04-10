from __future__ import annotations

import streamlit as st

from app.core.database import create_alert_profile, query_df
from app.ui import inject_css

st.set_page_config(page_title='Central de Alertas', page_icon='🔔', layout='wide')
inject_css()

st.title('🔔 Central de Alertas')
st.caption('Cadastro simples e direto. Pensado para o usuário final, não para técnico.')

left, right = st.columns([1.15, 1], gap='large')
with left:
    with st.form('alert_form'):
        st.markdown('### Novo perfil de alerta')
        name = st.text_input('Nome do alerta', placeholder='Ex.: Material gráfico BA')
        keywords = st.text_input('Palavras-chave', placeholder='material gráfico, impressos, banners')
        c1, c2, c3 = st.columns(3)
        state = c1.text_input('UF', placeholder='BA')
        city = c2.text_input('Município', placeholder='Salvador')
        modality = c3.text_input('Modalidade', placeholder='Pregão Eletrônico')
        min_value = st.number_input('Valor mínimo estimado', min_value=0.0, value=0.0, step=10000.0)
        email = st.text_input('E-mail para aviso', placeholder='licitacoes@empresa.com.br')
        telegram = st.text_input('Chat ID do Telegram', placeholder='Opcional')
        submitted = st.form_submit_button('Salvar perfil', use_container_width=True)
        if submitted:
            if not name.strip():
                st.error('Informe o nome do alerta.')
            else:
                create_alert_profile({
                    'name': name.strip(),
                    'keywords': keywords.strip(),
                    'state': state.strip().upper(),
                    'city': city.strip(),
                    'modality': modality.strip(),
                    'min_value': min_value,
                    'email': email.strip(),
                    'telegram_chat_id': telegram.strip(),
                    'active': True,
                })
                st.success('Perfil salvo com sucesso.')

with right:
    st.markdown('### Como o alerta deve funcionar')
    st.info('1. O GitHub Actions roda a atualização.\n2. A base local recebe novos avisos.\n3. O perfil cruza palavra, local, modalidade e valor.\n4. O sistema dispara a entrega configurada.')

st.markdown('### Perfis cadastrados')
profiles = query_df('SELECT id, name, keywords, state, city, modality, min_value, email, telegram_chat_id, active, created_at FROM alert_profiles ORDER BY id DESC')
if profiles.empty:
    st.caption('Nenhum perfil cadastrado ainda.')
else:
    st.dataframe(profiles, use_container_width=True, hide_index=True)

st.markdown('### Log de entregas')
log = query_df('SELECT created_at, alert_profile_id, notice_source_id, channel, status, details FROM delivery_log ORDER BY id DESC LIMIT 30')
if log.empty:
    st.caption('Sem entregas registradas até o momento.')
else:
    st.dataframe(log, use_container_width=True, hide_index=True)
