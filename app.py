from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from core import mercadopago
from core.access import FREE_PREVIEW_LIMIT, obfuscate_items, register_checkout, sync_email_subscription
from core.auth import ensure_user, get_user_email, valid_email
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
    top_by_state,
)
from core.storage import init_db

setup_page('MS Radar V10', '📡')
init_db()
logo_path = Path(__file__).parent / 'assets' / 'logo_ms_radar.png'
logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()

if 'refresh_nonce' not in st.session_state:
    st.session_state.refresh_nonce = 0

email_from_query = st.query_params.get('email')
if email_from_query and 'user_email' not in st.session_state and valid_email(str(email_from_query)):
    st.session_state['user_email'] = str(email_from_query).lower()

conn = test_connection()
status = f"Conexão ativa com o PNCP • ~{conn['latency_ms']} ms" if conn.get('ok') else 'Conexão instável com o PNCP agora'

user_email = get_user_email()
active_sub = None
subs = []
sync_error = None
if user_email:
    active_sub, subs, sync_error = sync_email_subscription(user_email)

premium = bool(active_sub)
checkout_notice = ''
if st.query_params.get('checkout') == 'retorno' and user_email:
    checkout_notice = 'Retorno do checkout detectado. O MS Radar já validou sua assinatura automaticamente.'

hero = f'''
<div class="hero">
  <div class="hero-top">
    <span class="ribbon">MS Radar • V10 assinatura recorrente</span>
    <span class="ribbon">PNCP em tempo real • sem banco de licitações</span>
    <span class="ribbon">Mercado Pago • cobrança recorrente</span>
  </div>
  <div style="display:flex;gap:24px;align-items:center;flex-wrap:wrap;margin-top:12px;">
    <img src="data:image/png;base64,{logo_b64}" style="width:190px;border-radius:16px;" />
    <div>
      <h1>MS Radar V10: produto recorrente com acesso premium automático, sem perder a velocidade da vitrine principal</h1>
      <p>Esta versão separa duas camadas: licitações continuam em modo espelho, sem armazenamento persistente, e a monetização passa a ter controle próprio para assinatura recorrente, liberação automática e renovação via Mercado Pago.</p>
      <p class="note-line">{status}</p>
      {f'<p class="note-line">{checkout_notice}</p>' if checkout_notice else ''}
    </div>
  </div>
</div>
'''
st.markdown(hero, unsafe_allow_html=True)

st.markdown('<div class="section-title">Acesso do assinante</div>', unsafe_allow_html=True)
left, right = st.columns([1.2, 1])
with left:
    with st.form('login-form', clear_on_submit=False):
        email_input = st.text_input('Seu e-mail de acesso', value=user_email or '', placeholder='voce@empresa.com.br')
        submitted = st.form_submit_button('Entrar / atualizar acesso', use_container_width=True)
        if submitted:
            try:
                user_email = ensure_user(email_input)
                active_sub, subs, sync_error = sync_email_subscription(user_email)
                premium = bool(active_sub)
                st.success('Acesso identificado com sucesso.')
            except Exception as exc:
                st.error(str(exc))
with right:
    if user_email:
        plan_text = 'Assinatura premium ativa' if premium else 'Modo demonstração / gratuito'
        note = f"Plano: {active_sub.get('plan_code','premium')} • status {active_sub.get('status')}" if premium else f"Prévia liberada com {FREE_PREVIEW_LIMIT} oportunidades completas antes do bloqueio leve."
        st.markdown(f'<div class="kpi"><div class="label">Status de acesso</div><div class="value">{plan_text}</div><div class="note">{note}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="kpi"><div class="label">Status de acesso</div><div class="value">Identifique-se</div><div class="note">Digite seu e-mail para liberar checkout, validar assinatura e manter o acesso recorrente.</div></div>', unsafe_allow_html=True)

if sync_error:
    st.warning(f'Não foi possível validar uma assinatura agora: {sync_error}')

st.markdown('<div class="section-title">Planos recorrentes</div>', unsafe_allow_html=True)
plans_cols = st.columns(2)
for idx, code in enumerate(['mensal', 'anual']):
    plan = mercadopago.PLANS[code]
    with plans_cols[idx]:
        st.markdown(
            f'''<div class="surface">
<strong>{plan.name}</strong>
<div style="font-size:2rem;font-weight:900;margin-top:8px;">{money_br(plan.amount)}</div>
<div class="small" style="margin-top:4px;">Cobrança recorrente a cada {plan.frequency} {plan.frequency_type}</div>
<ul>
<li>Busca avançada ampliada</li>
<li>Vitrine completa sem bloqueio</li>
<li>Validação automática do acesso</li>
<li>Renovação recorrente via Mercado Pago</li>
</ul>
</div>''',
            unsafe_allow_html=True,
        )
        disabled = (not user_email) or (not mercadopago.configured())
        if st.button(f'Assinar {plan.name}', key=f'assinar-{code}', use_container_width=True, disabled=disabled):
            try:
                checkout = register_checkout(user_email, code)
                link = checkout.get('init_point') or checkout.get('sandbox_init_point')
                if link:
                    st.markdown(f'<div class="cta-box"><strong>Checkout criado.</strong><div class="small" style="margin-top:8px;">Abra o link abaixo para concluir a assinatura e, ao retornar, o sistema validará seu acesso automaticamente.</div><div style="margin-top:12px;"><a class="btn-link" href="{link}" target="_blank">Abrir checkout do Mercado Pago</a></div></div>', unsafe_allow_html=True)
                else:
                    st.success('Assinatura criada, mas o link de checkout não foi retornado. Verifique o payload do Mercado Pago.')
            except Exception as exc:
                st.error(f'Falha ao criar checkout: {exc}')

if not mercadopago.configured():
    st.info('Configure MP_ACCESS_TOKEN e PUBLIC_APP_URL em variáveis de ambiente ou st.secrets para ativar a assinatura recorrente.')

st.markdown('<div class="section-title">Painel principal do radar</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">A vitrine continua rápida. O que muda no V10 é a camada de acesso recorrente, não a filosofia de espelho do PNCP.</div>', unsafe_allow_html=True)
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

render_feed = obfuscate_items(home_feed, premium)
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
    if premium:
        st.markdown('<div class="cta-box"><strong>Acesso premium liberado</strong><div class="small" style="margin-top:8px;">Você vê a vitrine completa e a assinatura seguirá renovando pelo Mercado Pago enquanto estiver ativa.</div></div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="cta-box"><strong>Prévia gratuita ativa</strong><div class="small" style="margin-top:8px;">Você está vendo {FREE_PREVIEW_LIMIT} oportunidades completas. Para liberar a vitrine integral e a busca avançada ampliada, ative uma assinatura recorrente.</div></div>', unsafe_allow_html=True)
    if home_feed:
        csv = export_df(home_feed if premium else home_feed[:FREE_PREVIEW_LIMIT]).to_csv(index=False).encode('utf-8-sig')
        st.download_button('Baixar CSV disponível no seu plano', data=csv, file_name='ms_radar_vitrine.csv', mime='text/csv', use_container_width=True)

if not premium and len(home_feed) > FREE_PREVIEW_LIMIT:
    st.markdown('<div class="section-title">Bloqueio leve de monetização</div>', unsafe_allow_html=True)
    st.markdown('<div class="cta-box"><strong>Você está vendo uma prévia do MS Radar.</strong><div class="small" style="margin-top:8px;">As próximas oportunidades ficaram ocultas para demonstrar valor sem travar a experiência. Com assinatura ativa, a vitrine completa, os filtros ampliados e as exportações premium ficam liberados automaticamente.</div></div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">Encerra hoje</div>', unsafe_allow_html=True)
render_cards(obfuscate_items(urgentes[:6], premium), columns=3)

st.markdown('<div class="section-title">Maior valor</div>', unsafe_allow_html=True)
render_cards(obfuscate_items(alto_valor[:6], premium), columns=3)

st.markdown('<div class="section-title">Oportunidades da Bahia</div>', unsafe_allow_html=True)
render_cards(obfuscate_items(feed_bahia or feed_nordeste, premium), columns=3)

st.markdown('<div class="section-title">Busca avançada sob demanda</div>', unsafe_allow_html=True)
st.markdown('<div class="section-sub">No plano gratuito a busca avançada é mais curta. No premium, o limite cresce e a exportação sai completa.</div>', unsafe_allow_html=True)
a1, a2, a3 = st.columns([1, 0.8, 0.8])
with a1:
    default_limit = 20 if premium else 8
    limit = st.slider('Máximo de resultados', min_value=6, max_value=40 if premium else 12, value=default_limit, step=2)
with a2:
    endpoint = st.selectbox('Tipo de leitura', ['proposta', 'publicacao'], index=0)
with a3:
    selected_niche = st.selectbox('Nicho', ['Todos'] + list(NICHES.keys()), index=0)

if st.button('Rodar busca avançada', use_container_width=True):
    with st.spinner('Consultando o PNCP com recorte ampliado...'):
        adv_feed = fetch_feed(
            termo=termo,
            uf=uf,
            modalidades=modalidades or FAST_HOME_MODALIDADES,
            endpoint=endpoint,
            max_per_modality=10 if premium else 4,
            page_size=20 if premium else 10,
            niche_filter=None if selected_niche == 'Todos' else selected_niche,
        )[:limit]
    render_cards(obfuscate_items(adv_feed, premium), columns=3)
    if adv_feed:
        csv = export_df(adv_feed if premium else adv_feed[:FREE_PREVIEW_LIMIT]).to_csv(index=False).encode('utf-8-sig')
        st.download_button('Baixar resultado desta busca', data=csv, file_name='ms_radar_busca.csv', mime='text/csv', use_container_width=True)

if user_email and subs:
    st.markdown('<div class="section-title">Histórico de assinaturas do e-mail</div>', unsafe_allow_html=True)
    rows = []
    for item in subs[:10]:
        rows.append({
            'plano': item.get('plan_code'),
            'status': item.get('status'),
            'valor': money_br(item.get('amount') or 0),
            'referência': item.get('external_reference'),
            'criado em': item.get('created_at'),
            'atualizado em': item.get('updated_at'),
        })
    st.dataframe(rows, use_container_width=True)
