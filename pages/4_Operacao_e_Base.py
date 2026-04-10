from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from app.core.database import insert_sync_history, query_df, upsert_notices
from app.core.pncp_client import fetch_open_notices, load_demo_notices, normalize_item
from app.ui import inject_css

st.set_page_config(page_title='Operação e Base', page_icon='🗂️', layout='wide')
inject_css()

st.title('🗂️ Operação e Base')
st.caption('Área de operação para quem administra a ferramenta.')

c1, c2, c3 = st.columns(3)
if c1.button('Sincronizar PNCP (30 dias)', use_container_width=True):
    try:
        notices = fetch_open_notices(days_ahead=30)
        total = upsert_notices(notices)
        insert_sync_history('pncp', total, 'ok', 'Operação manual via página de administração')
        st.success(f'{total} registros sincronizados do PNCP.')
    except Exception as exc:
        st.error(f'Falha na sincronização: {exc}')
if c2.button('Recarregar base demo', use_container_width=True):
    notices = load_demo_notices()
    total = upsert_notices(notices)
    insert_sync_history('demo', total, 'ok', 'Recarga demo')
    st.success(f'{total} registros demo importados.')
if c3.button('Atualizar tela', use_container_width=True):
    st.rerun()

st.markdown('### Importação manual de JSON')
uploaded = st.file_uploader('Envie um arquivo JSON com dados de oportunidades', type=['json'])
if uploaded is not None:
    import json
    payload = json.load(uploaded)
    rows = payload.get('data') if isinstance(payload, dict) else payload
    notices = []
    for item in rows:
        try:
            if 'source_id' in item:
                from app.core.models import Notice
                notices.append(Notice(**item))
            else:
                notices.append(normalize_item(item))
        except Exception:
            continue
    total = upsert_notices(notices)
    insert_sync_history('json', total, 'ok', 'Importação manual JSON')
    st.success(f'Importação concluída com {total} registros.')

st.markdown('### Exportação da base')
base = query_df('SELECT * FROM notices ORDER BY publication_date DESC')
if not base.empty:
    st.download_button('Baixar CSV da base', data=base.to_csv(index=False).encode('utf-8-sig'), file_name='radar_licitacoes.csv', mime='text/csv')
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        base.to_excel(writer, index=False, sheet_name='Oportunidades')
    st.download_button('Baixar Excel da base', data=output.getvalue(), file_name='radar_licitacoes.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

st.markdown('### Visões salvas')
views = query_df('SELECT id, name, query_json, created_at FROM saved_views ORDER BY id DESC')
if views.empty:
    st.caption('Nenhuma visão salva.')
else:
    st.dataframe(views, use_container_width=True, hide_index=True)
