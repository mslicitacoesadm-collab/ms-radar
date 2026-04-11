from __future__ import annotations

import base64
from pathlib import Path
from urllib.parse import quote_plus

import streamlit as st

from core.monetizacao import FREE_PREVIEW_LIMIT, ensure_state, obfuscate_items, premium_active, reset_access, unlock_premium
from core.pncp import (
    FAST_HOME_MODALIDADES,
    MAX_HOME_ITEMS,
    MODALIDADES,
    NICHES,
    STATE_GROUPS,
    UFS,
    export_df,
    fetch_feed,
    filter_high_value,
    filter_urgent,
    kpis_for,
    money_br,
    render_cards,
    setup_page,
    test_connection,
    top_by_niche,
    top_by_state,
)

setup_page('MS Radar V8', '📡')
ensure_state()

logo_path = Path(__file__).parent / 'assets' / 'logo_ms_radar.png'
logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()

if 'refresh_nonce' not in st.session_state:
    st.session_state.refresh_nonce = 0

conn = test_connection()
status = f"Conexão ativa com o PNCP • ~{conn['latency_ms']} ms" if conn.get('ok') else 'Conexão instável com o PNCP agora'
premium = premium_active()

hero = f'''
<div class="hero">
  <div class="hero-top">
    <span class="ribbon">MS Radar • V8 monetização direta</span>
    <span class="ribbon">PNCP em tempo real • sem banco de licitações</span>
    <span class="ribbon">Prévia gratuita com bloqueio leve</span>
  </div>
  <div style="display:flex;gap:24px;align-items:center;flex-wrap:wrap;margin-top:12px;">
    <img src="data:image/png;base64,{logo_b64}" style="width:190px;border-radius:16px;" />
    <div>
      <h1>MS Radar V8: vitrine comercial rápida, leitura clara e monetização leve sem armazenamento persistente de licitações</h1>
      <p>Esta versão foi revisada para funcionar como uma entrada premium do PNCP: carrega rápido, concentra toda a navegação na página principal e demonstra monetização por prévia gratuita, sem ainda depender de checkout externo.</p>
      <p class="note-line">{status}</p>
    </div>
  </div>
</div>
'''
st.markdown(hero, unsafe_allow_html=True)

st.markdown('<div class="section-title">Camada de monetização</div>', unsafe_allow_html=True)
m1, m2, m3 = st.columns([1.2, 1, 1])
with m1:
    msg = 'Acesso premium liberado nesta sessão.' if premium else f'Prévia gratuita com {FREE_PREVIEW_LIMIT} oportunidades completas por vitrine.'
    st.markdown(f'<div class="kpi"><div class="label">Status do acesso</div><div class="value">{"Premium" if premium else "Prévia"}</div><div class="note">{msg}</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown('<div class="kpi"><div class="label">Estratégia</div><div class="value">Paywall leve</div><div class="note">A V8 demonstra valor mostrando parte das oportunidades e ocultando o restante.</div></div>', unsafe_allow_html=True)
with m3:
    if premium:
        if st.button('Voltar para modo prévia', use_container_width=True):
            reset_access()
            st.rerun()
    else:
        if st.button('Simular desbloqueio premium', use_container_width=True):
            unlock_premium()
            st.rerun()

with st.container():
    f1, f2, f3, f4, f5 = st.columns([1.35, 0.8, 1.1, 1.5, 0.8])
    with f1:
        termo = st.text_input('Palavra-chave', placeholder='Ex.: limpeza, transporte, medicamentos')
    with f2:
        uf = st.selectbox('UF', UFS, index=0)
    with f3:
        regiao = st.selectbox('Região', ['Brasil'] + list(STATE_GROUPS.keys()), index=0)
    with f4:
        modalidades = st.multiselect('Modalidades', options=list(MODALIDADES.keys()), default=FAST_HOME_MODALIDADES, format_func=lambda x: MODALIDADES.get(x, str(x)))
    with f5:
        st.write('')
        st.write('')
        if st.button('Atualizar radar', use_container_width=True):
            st.cache_data.clear()
            st.session_state.refresh_nonce += 1
            st.rerun()

with st.spinner('Carregando vitrine principal do MS Radar...'):
    home_feed = fetch_feed(
        termo=termo,
        uf=uf,
        modalidades=modalidades or FAST_HOME_MODALIDADES,
        max_per_modality=5,
        page_size=10,
    )[:MAX_HOME_ITEMS]

render_feed = obfuscate_items(home_feed)
urgentes = filter_urgent(home_feed)
alto_valor = filter_high_value(home_feed)
feed_bahia = top_by_state(home_feed, 'BA', limit=6)
feed_nordeste = [x for x in home_feed if x.get('uf') in STATE_GROUPS['Nordeste']][:6]

k = kpis_for(home_feed)
k1, k2, k3, k4 = st.columns(4)
for col, label, value, note in [
    (k1, 'Licitações na entrada', str(k['total']), 'Já aparecem sem clique inicial'),
    (k2, 'Urgentes', str(k['urgentes']), 'Encerram hoje ou em prazo curto'),
    (k3, 'Alto valor', str(k['alto_valor']), 'Mais potencial comercial imediato'),
    (k4, 'Valor estimado', money_br(k['valor_total']), 'Soma do feed atual'),
]:
    with col:
        st.markdown(f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div><div class="note">{note}</div></div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">Vitrine principal</div>', unsafe_allow_html=True)
left, right = st.columns([1.45, 0.55])
with left:
    render_cards(render_feed, columns=3)
with right:
    st.markdown('<div class="cta-box"><strong>Mensagem comercial pronta</strong><div class="small" style="margin-top:8px;">O MS Radar consulta o PNCP em tempo real e transforma dados brutos em uma vitrine rápida, clara e comercialmente útil.</div></div>', unsafe_allow_html=True)
    if premium:
        st.markdown('<div class="cta-box"><strong>Acesso premium liberado</strong><div class="small" style="margin-top:8px;">Nesta revisão da V8, o premium é simulado para validar a experiência comercial antes de integrar pagamento real.</div></div>', unsafe_allow_html=True)
        export_items = home_feed
    else:
        st.markdown(f'<div class="cta-box"><strong>Prévia gratuita ativa</strong><div class="small" style="margin-top:8px;">Você está vendo {FREE_PREVIEW_LIMIT} oportunidades completas nesta vitrine. As próximas foram ocultadas para demonstrar a camada de monetização.</div></div>', unsafe_allow_html=True)
        export_items = home_feed[:FREE_PREVIEW_LIMIT]
    if export_items:
        csv = export_df(export_items).to_csv(index=False).encode('utf-8-sig')
        st.download_button('Baixar CSV disponível no plano atual', data=csv, file_name='ms_radar_vitrine_v8.csv', mime='text/csv', use_container_width=True)

if not premium and len(home_feed) > FREE_PREVIEW_LIMIT:
    st.markdown('<div class="section-title">Bloqueio leve de monetização</div>', unsafe_allow_html=True)
    st.markdown('<div class="cta-box"><strong>Você está vendo uma prévia do MS Radar.</strong><div class="small" style="margin-top:8px;">As próximas oportunidades ficaram ocultas para demonstrar valor sem travar a experiência. Na evolução com pagamento real, esta mesma lógica libera a vitrine completa automaticamente.</div></div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">Oportunidades que pedem ação rápida</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Licitações com encerramento mais próximo para priorização comercial.</div>', unsafe_allow_html=True)
render_cards(obfuscate_items(urgentes[:6]), columns=3)

st.markdown('<div class="section-title">Licitações de maior valor</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Recorte voltado para oportunidades com maior potencial financeiro.</div>', unsafe_allow_html=True)
render_cards(obfuscate_items(alto_valor[:6]), columns=3)

st.markdown('<div class="section-title">Oportunidades da Bahia</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Vitrine rápida do estado mais importante para sua operação.</div>', unsafe_allow_html=True)
render_cards(obfuscate_items(feed_bahia or feed_nordeste), columns=3)

st.markdown('<div class="section-title">Seções por nicho</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">Recortes pensados para facilitar prospecção por mercado.</div>', unsafe_allow_html=True)
selected_niche = st.selectbox('Escolha o nicho principal', list(NICHES.keys()))
niche_feed = top_by_niche(home_feed, selected_niche, limit=6)
if not niche_feed:
    with st.spinner('Buscando mais resultados do nicho selecionado...'):
        niche_feed = fetch_feed(
            termo=termo,
            uf=uf,
            modalidades=modalidades or FAST_HOME_MODALIDADES,
            max_per_modality=6,
            page_size=12,
            niche_filter=selected_niche,
        )[:6]
render_cards(obfuscate_items(niche_feed), columns=3)

st.markdown('<div class="section-title">Estados em evidência</div>', unsafe_allow_html=True)
state_options = UFS[1:] if regiao == 'Brasil' else STATE_GROUPS[regiao]
selected_state = st.selectbox('Escolha o estado para vitrine regional', state_options)
state_feed = top_by_state(home_feed, selected_state, limit=6)
if not state_feed:
    with st.spinner('Buscando oportunidades do estado selecionado...'):
        state_feed = fetch_feed(
            termo=termo,
            uf=selected_state,
            modalidades=modalidades or FAST_HOME_MODALIDADES,
            max_per_modality=6,
            page_size=12,
        )[:6]
render_cards(obfuscate_items(state_feed), columns=3)

st.markdown('<div class="section-title">Busca avançada sob demanda</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">A home continua rápida porque a consulta ampliada só roda quando você pedir.</div>', unsafe_allow_html=True)
a1, a2, a3 = st.columns([1, 0.8, 0.8])
with a1:
    limit = st.slider('Máximo de resultados', min_value=10, max_value=40, value=24, step=2)
with a2:
    endpoint = st.selectbox('Tipo de leitura', ['proposta', 'publicacao'], index=0)
with a3:
    sort_mode = st.selectbox('Ordenar por', ['Score comercial', 'Maior valor'])

if st.button('Rodar busca avançada', use_container_width=True):
    with st.spinner('Consultando o PNCP com recorte ampliado...'):
        adv_feed = fetch_feed(
            termo=termo,
            uf=uf,
            modalidades=modalidades or FAST_HOME_MODALIDADES,
            endpoint=endpoint,
            max_per_modality=10,
            page_size=20,
        )[:limit]
    if sort_mode == 'Maior valor':
        adv_feed = sorted(adv_feed, key=lambda x: float(x.get('valor') or 0), reverse=True)
    st.success(f'Busca concluída com {len(adv_feed)} resultados.')
    protected_adv = obfuscate_items(adv_feed)
    render_cards(protected_adv[:12], columns=3)
    visible_adv = adv_feed if premium else adv_feed[:FREE_PREVIEW_LIMIT]
    if visible_adv:
        csv = export_df(visible_adv).to_csv(index=False).encode('utf-8-sig')
        st.download_button('Baixar busca atual em CSV', data=csv, file_name='ms_radar_busca_avancada_v8.csv', mime='text/csv', use_container_width=True)

st.markdown('<div class="section-title">Inteligência comercial</div>', unsafe_allow_html=True)
ranked = sorted(home_feed, key=lambda x: (x.get('score', 0), x.get('valor') or 0), reverse=True)
search_term = quote_plus(termo) if termo else 'licitacao'
left, right = st.columns([1.05, 0.95])
with left:
    if not ranked:
        st.info('Sem dados para ranking agora.')
    else:
        visible_ranked = ranked if premium else ranked[:FREE_PREVIEW_LIMIT]
        for pos, item in enumerate(visible_ranked[:8], start=1):
            badge = '🏆' if pos == 1 else '⭐'
            st.markdown(f"{badge} **#{pos} — {item['objeto']}**  \\\n{item['municipio']}/{item['uf']} • {item['modalidade']} • {item['valor_formatado']} • {item['urgencia']}")
            if item.get('fonte'):
                st.markdown(f"[Abrir origem]({item['fonte']})")
with right:
    valor_total = sum(float(x.get('valor') or 0) for x in home_feed if str(x.get('valor') or '').strip())
    st.markdown(
        f'''
<div class="surface">
  <div style="font-size:1.08rem;font-weight:900;color:white;">Mensagem pronta para apresentação</div>
  <div class="small" style="margin-top:10px;">O MS Radar consulta o PNCP em tempo real e entrega uma entrada muito mais inteligente do que o portal bruto. Em vez de forçar o usuário a navegar em páginas frias, ele já mostra oportunidades com leitura comercial e recortes práticos para prospecção.</div>
  <div class="small" style="margin-top:10px;">No feed atual, a plataforma exibiu <strong>{len(home_feed)}</strong> oportunidades, com valor estimado somado de <strong>{money_br(valor_total)}</strong>.</div>
  <div class="small" style="margin-top:10px;">Esta revisão da V8 ficou pronta para demonstração comercial e preparação da camada de cobrança real na V9/V10.</div>
</div>
''',
        unsafe_allow_html=True,
    )
    st.link_button('Abrir busca pública do termo no Google', f'https://www.google.com/search?q={search_term}+pncp', use_container_width=True)
