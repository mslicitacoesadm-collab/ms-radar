from __future__ import annotations

import io
import json
from datetime import datetime

import pandas as pd
import streamlit as st

from app.core.config import load_settings
from app.core.database import (
    delete_alert,
    get_metrics,
    init_db,
    list_alerts,
    list_modalities,
    list_notices,
    list_states,
    list_sync_runs,
    save_alert,
    upsert_notices,
)
from app.core.pncp_client import PNCPClient
from app.core.search_engine import filter_and_rank, priority_label
from app.services.sync_job import run_sync

st.set_page_config(page_title="Radar Inteligente de Licitações", page_icon="📡", layout="wide")

init_db()
settings = load_settings()
client = PNCPClient()

st.markdown(
    """
    <style>
    .hero {padding: 1.25rem 1.5rem; border: 1px solid rgba(255,255,255,.08); border-radius: 22px;
           background: linear-gradient(135deg, rgba(19,78,94,.65), rgba(15,23,42,.9));}
    .hero h1 {margin: 0; font-size: 2rem;}
    .hero p {margin: .4rem 0 0 0; opacity: .92;}
    .pill {display:inline-block; padding: .2rem .6rem; border-radius:999px; margin-right:.45rem;
           border:1px solid rgba(255,255,255,.15); font-size:.85rem;}
    .card {padding: 1rem; border-radius: 18px; border: 1px solid rgba(255,255,255,.08); background: rgba(255,255,255,.02);}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <span class="pill">PNCP ready</span>
      <span class="pill">GitHub Actions</span>
      <span class="pill">Alertas inteligentes</span>
      <h1>Radar Inteligente de Licitações</h1>
      <p>Buscador profissional com filtros avançados, score de relevância, alertas e rotina automatizada de atualização.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

metrics = get_metrics()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Licitações na base", metrics["notices"])
c2.metric("Alertas ativos", metrics["alerts"])
c3.metric("Órgãos distintos", metrics["agencies"])
c4.metric("UFs cobertas", metrics["states"])

menu = st.sidebar.radio(
    "Navegação",
    ["Busca inteligente", "Alertas", "Operação / carga", "Painel técnico"],
)

if menu == "Busca inteligente":
    st.subheader("Busca inteligente de licitações")
    base_rows = [dict(row) for row in list_notices(limit=2000)]
    base_df = pd.DataFrame(base_rows)

    if base_df.empty:
        st.info("A base está vazia. Vá em 'Operação / carga' e rode uma sincronização inicial.")
    else:
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        query = col1.text_input("Objeto, tese comercial ou palavra-chave", placeholder="Ex.: material de limpeza, combustível, software, merenda escolar")
        state = col2.selectbox("UF", [""] + list_states())
        city = col3.text_input("Município")
        modality = col4.selectbox("Modalidade", [""] + list_modalities())

        col5, col6 = st.columns(2)
        min_value = col5.number_input("Valor mínimo estimado", min_value=0.0, step=1000.0)
        max_value = col6.number_input("Valor máximo estimado", min_value=0.0, step=1000.0)

        result = filter_and_rank(base_df, query, state, city, modality, min_value, max_value)
        st.caption(f"Resultados encontrados: {len(result)}")

        if not result.empty:
            display_cols = [
                "title",
                "agency",
                "city",
                "state",
                "modality",
                "estimated_value",
                "publication_date",
                "deadline_date",
                "source_url",
                "score",
            ]
            result["prioridade"] = result["score"].apply(priority_label)
            ordered = result[["prioridade"] + display_cols].copy()
            ordered = ordered.rename(columns={
                "title": "Título",
                "agency": "Órgão",
                "city": "Cidade",
                "state": "UF",
                "modality": "Modalidade",
                "estimated_value": "Valor estimado",
                "publication_date": "Publicação",
                "deadline_date": "Prazo",
                "source_url": "Link",
                "score": "Score",
            })
            st.dataframe(ordered, use_container_width=True, hide_index=True)

            csv = ordered.to_csv(index=False).encode("utf-8-sig")
            st.download_button("Baixar resultados em CSV", data=csv, file_name="radar_licitacoes_resultados.csv", mime="text/csv")

            with st.expander("Ver cards de oportunidade"):
                for _, row in result.head(30).iterrows():
                    st.markdown(f"### {row['title']}")
                    st.markdown(
                        f"**Prioridade:** {priority_label(row['score'])} | **Score:** {row['score']}  \n"
                        f"**Órgão:** {row['agency']}  \n"
                        f"**Cidade/UF:** {row['city']}/{row['state']}  \n"
                        f"**Modalidade:** {row['modality']}  \n"
                        f"**Valor estimado:** R$ {float(row['estimated_value'] or 0):,.2f}  \n"
                        f"**Publicação:** {row['publication_date']}  \n"
                        f"**Prazo:** {row['deadline_date']}  \n"
                        f"**Fonte:** {row['source_system']}"
                    )
                    if str(row.get("source_url", "")).strip():
                        st.link_button("Abrir fonte", str(row["source_url"]))
                    st.divider()
        else:
            st.warning("Nenhum resultado aderente aos filtros informados.")

elif menu == "Alertas":
    st.subheader("Perfis de alerta")

    with st.form("novo_alerta"):
        a1, a2 = st.columns(2)
        name = a1.text_input("Nome do alerta", placeholder="Ex.: Combustível Bahia")
        keywords = a2.text_input("Palavras-chave", placeholder="Ex.: combustível gasolina diesel")
        b1, b2, b3 = st.columns(3)
        state = b1.text_input("UF")
        city = b2.text_input("Município")
        modality = b3.text_input("Modalidade")
        c1, c2 = st.columns(2)
        min_value = c1.number_input("Valor mínimo", min_value=0.0, step=1000.0, key="alert_min")
        max_value = c2.number_input("Valor máximo", min_value=0.0, step=1000.0, key="alert_max")
        d1, d2 = st.columns(2)
        email = d1.text_input("E-mail para aviso")
        telegram_chat_id = d2.text_input("Telegram chat_id")
        submitted = st.form_submit_button("Salvar alerta")
        if submitted:
            if not name.strip():
                st.error("Informe um nome para o alerta.")
            else:
                alert_id = save_alert(
                    {
                        "name": name,
                        "keywords": keywords,
                        "state": state,
                        "city": city,
                        "modality": modality,
                        "min_value": min_value,
                        "max_value": max_value,
                        "email": email,
                        "telegram_chat_id": telegram_chat_id,
                        "is_active": 1,
                    }
                )
                st.success(f"Alerta salvo com sucesso. ID: {alert_id}")

    alerts = [dict(row) for row in list_alerts()]
    if alerts:
        st.markdown("### Alertas cadastrados")
        for item in alerts:
            box = st.container(border=True)
            with box:
                st.markdown(f"**#{item['id']} — {item['name']}**")
                st.write(
                    f"Palavras-chave: {item['keywords'] or '-'} | UF: {item['state'] or '-'} | Cidade: {item['city'] or '-'} | "
                    f"Modalidade: {item['modality'] or '-'} | Faixa: R$ {float(item['min_value'] or 0):,.2f} até R$ {float(item['max_value'] or 0):,.2f}"
                )
                st.write(f"Destino e-mail: {item['email'] or '-'} | Telegram: {item['telegram_chat_id'] or '-'}")
                if st.button(f"Excluir alerta {item['id']}", key=f"del_{item['id']}"):
                    delete_alert(int(item["id"]))
                    st.rerun()
    else:
        st.info("Nenhum alerta cadastrado ainda.")

elif menu == "Operação / carga":
    st.subheader("Carga manual e sincronização")
    st.write("Use esta área para alimentar a base, fazer sincronização de teste e validar o motor de alertas.")

    x1, x2 = st.columns(2)
    if x1.button("Sincronizar agora (API ou demo)", use_container_width=True):
        result = run_sync(query="", days=30)
        st.success(f"Sincronização concluída. Encontrados: {result['found']} | Novos: {result['inserted']} | Alertas enviados: {result['deliveries']}")

    if x2.button("Carregar base de demonstração", use_container_width=True):
        sample = client.load_sample()
        found, inserted = upsert_notices(sample)
        st.success(f"Base demo carregada. Itens processados: {found} | Novos: {inserted}")

    upload = st.file_uploader("Importar JSON do PNCP / fonte externa", type=["json"])
    if upload is not None:
        try:
            rows = client.import_json_file(upload.read())
            found, inserted = upsert_notices(rows)
            st.success(f"Importação concluída. Processados: {found} | Novos: {inserted}")
        except Exception as exc:
            st.error(f"Falha ao importar arquivo: {exc}")

    st.markdown("### Estado técnico da integração")
    st.code(
        json.dumps(
            {
                "pncp_search_url_configurada": bool(settings.pncp_search_url),
                "timeout": settings.pncp_timeout,
                "sync_sample_if_empty": settings.sync_sample_if_empty,
                "smtp_configurado": bool(settings.smtp_host and settings.smtp_user and settings.smtp_password),
                "telegram_configurado": bool(settings.telegram_bot_token),
            },
            ensure_ascii=False,
            indent=2,
        ),
        language="json",
    )

elif menu == "Painel técnico":
    st.subheader("Painel técnico e auditoria operacional")
    runs = [dict(row) for row in list_sync_runs(limit=50)]
    notices = [dict(row) for row in list_notices(limit=20)]

    s1, s2 = st.columns(2)
    with s1:
        st.markdown("### Últimas sincronizações")
        if runs:
            st.dataframe(pd.DataFrame(runs), use_container_width=True, hide_index=True)
        else:
            st.info("Ainda não há logs de sincronização.")
    with s2:
        st.markdown("### Últimas licitações na base")
        if notices:
            preview = pd.DataFrame(notices)[["source_id", "title", "agency", "city", "state", "deadline_date", "source_system"]]
            st.dataframe(preview, use_container_width=True, hide_index=True)
        else:
            st.info("A base ainda não possui registros.")

    st.markdown("### Arquitetura recomendada")
    st.markdown(
        "- Streamlit para interface e operação\n"
        "- GitHub Actions para sincronização agendada\n"
        "- SQLite para MVP sem custo\n"
        "- SMTP ou Telegram para entrega de alertas\n"
        "- Evolução futura para API própria e banco gerenciado"
    )
