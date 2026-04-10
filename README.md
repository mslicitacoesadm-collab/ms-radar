# Radar Inteligente de Licitações

Aplicação em Streamlit para busca inteligente de licitações, operação com base local SQLite, filtros comerciais e cadastro de alertas.

## O que já funciona

- busca local com score de relevância
- sincronização real com a API de consultas do PNCP
- carga de base demo para apresentação
- importação manual de JSON externo
- cadastro de alertas na base SQLite
- envio de alertas por e-mail e Telegram
- workflow do GitHub Actions para atualizar a base

## Base técnica PNCP

A integração foi ajustada com base na documentação oficial do PNCP:

- URL base de serviços: `https://pncp.gov.br/api/consulta`
- endpoint de consultas com propostas abertas: `/v1/contratacoes/proposta`
- endpoint de detalhe da contratação: `/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}`

## Estrutura

```text
app.py
app/
  assets/sample_notices.json
  core/
    alerts.py
    config.py
    database.py
    models.py
    pncp_client.py
    search_engine.py
  services/
    sync_job.py
.github/workflows/sync_alerts.yml
data/
requirements.txt
```

## Rodando localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Secrets recomendados no Streamlit e no GitHub

```toml
PNCP_SEARCH_URL="https://pncp.gov.br/api/consulta"
PNCP_TIMEOUT="25"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER="seu-email@gmail.com"
SMTP_PASSWORD="senha-ou-app-password"
SMTP_FROM="seu-email@gmail.com"
TELEGRAM_BOT_TOKEN="123456:ABCDEF"
TELEGRAM_CHAT_ID="123456789"
```

## Deploy no GitHub + Streamlit

1. Suba todo o projeto para um repositório GitHub.
2. No Streamlit Community Cloud, crie um app apontando para `app.py`.
3. Cadastre os mesmos secrets acima no painel do Streamlit.
4. No GitHub, habilite Actions e adicione os mesmos secrets no repositório.
5. Execute o workflow `Sincronizar radar de licitações` manualmente na primeira vez.

## Observação importante sobre persistência

No modelo GitHub + Streamlit Community Cloud, o banco SQLite é excelente para MVP e operação simples, mas a persistência do arquivo no app depende do ambiente do Streamlit. Por isso o workflow do GitHub também salva o banco no repositório, permitindo manter uma base atualizada para novas execuções.

## Próximas evoluções sugeridas

- detalhe completo da contratação na interface
- resumo automático do edital
- score de oportunidade comercial
- leitura de risco jurídico
- integração com geração de impugnação, recurso e contrarrazão
