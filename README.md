# Radar Licita Pro

Versão profissional em Streamlit para busca simples, operação rápida e centro de alertas de licitações.

## O que esta versão entrega

- interface mais limpa e comercial
- busca inteligente com score de aderência e oportunidade
- radar diário com priorização por urgência, valor e fit
- central de alertas com cadastro simples
- painel de operação para sincronizar, importar e exportar
- integração com a API de consultas do PNCP
- workflow pronto para GitHub Actions

## Estrutura

```text
app.py
pages/
  1_Busca_Inteligente.py
  2_Radar_Diario.py
  3_Central_de_Alertas.py
  4_Operacao_e_Base.py
app/
  core/
  services/
  assets/
.github/workflows/
data/
```

## Rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Secrets recomendados

```toml
PNCP_SEARCH_URL="https://pncp.gov.br/api/consulta"
PNCP_TIMEOUT="25"
SMTP_HOST="smtp.gmail.com"
SMTP_PORT="587"
SMTP_USER="seu-email@gmail.com"
SMTP_PASSWORD="sua-senha-ou-app-password"
SMTP_FROM="seu-email@gmail.com"
TELEGRAM_BOT_TOKEN="123456:ABCDEF"
TELEGRAM_CHAT_ID="123456789"
```

## Rotina ideal

1. Subir o projeto no GitHub.
2. Criar o app no Streamlit apontando para `app.py`.
3. Configurar os secrets no Streamlit.
4. Habilitar GitHub Actions e cadastrar os mesmos secrets.
5. Rodar manualmente o workflow na primeira vez.
6. Usar a tela inicial para validar base demo ou sincronização do PNCP.

## Observação técnica

A integração foi preparada com base na documentação de consultas do PNCP: URL base `https://pncp.gov.br/api/consulta`, endpoint de oportunidades abertas `/v1/contratacoes/proposta` e consulta de detalhe da contratação em `/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}`.

## Próxima camada premium

- leitura de risco do edital
- score comercial por nicho
- resumo executivo pronto para equipe de vendas
- integração com módulo jurídico
