from __future__ import annotations

import streamlit as st

from app.core.database import Database
from app.ui import hero, opportunity_card, set_page


set_page('Busca Suprema')
db = Database()
hero('Busca Suprema', 'Pesquisa limpa e direta sobre oportunidades reais já sincronizadas do PNCP.')

ufs = [''] + db.distinct_values('uf_sigla') if db.stats()['total'] else ['']
municipios = [''] + db.distinct_values('municipio_nome') if db.stats()['total'] else ['']

c1, c2, c3, c4 = st.columns([3, 1, 2, 1.4])
with c1:
    termo = st.text_input('O que você procura?', placeholder='Ex.: material gráfico, combustível, merenda, software')
with c2:
    uf = st.selectbox('UF', ufs)
with c3:
    municipio = st.selectbox('Município', municipios)
with c4:
    somente_abertas = st.toggle('Só abertas', value=True)

c5, c6, c7 = st.columns(3)
with c5:
    valor_min = st.number_input('Valor mínimo', min_value=0.0, value=0.0, step=1000.0)
with c6:
    ordem = st.selectbox('Ordenar por', ['Melhor score', 'Prazo mais próximo', 'Maior valor'])
with c7:
    limite = st.selectbox('Quantidade', [20, 50, 100], index=1)

if db.stats()['total'] == 0:
    st.warning('A base ainda está vazia. Vá para a página Operação PNCP e execute a primeira sincronização.')
    st.stop()

where = []
params: list = []

if termo:
    tokens = [t.strip() for t in termo.split() if t.strip()]
    if tokens:
        sub = []
        for token in tokens:
            sub.append('search_blob LIKE ?')
            params.append(f'%{token.lower()}%')
        where.append('(' + ' AND '.join(sub) + ')')
if uf:
    where.append('uf_sigla = ?')
    params.append(uf)
if municipio:
    where.append('municipio_nome = ?')
    params.append(municipio)
if valor_min > 0:
    where.append('valor_total_estimado >= ?')
    params.append(valor_min)
if somente_abertas:
    where.append("date(data_encerramento_proposta) >= date('now')")

sql = 'SELECT * FROM opportunities'
if where:
    sql += ' WHERE ' + ' AND '.join(where)
if ordem == 'Melhor score':
    sql += ' ORDER BY oportunidade_score DESC, data_encerramento_proposta ASC'
elif ordem == 'Prazo mais próximo':
    sql += ' ORDER BY data_encerramento_proposta ASC, oportunidade_score DESC'
else:
    sql += ' ORDER BY valor_total_estimado DESC, oportunidade_score DESC'
sql += ' LIMIT ?'
params.append(limite)

rows = db.export_rows(sql, tuple(params))

st.caption(f'{len(rows)} resultado(s) encontrados.')
for row in rows:
    opportunity_card(dict(row))
