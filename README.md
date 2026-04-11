# Radar Espelho PNCP

Projeto Streamlit em **modo espelho**, sem banco de dados e sem persistência local.

## O que esta versão faz

- conecta automaticamente com a API pública do PNCP ao entrar no site
- consulta licitações ao vivo
- não usa SQLite
- não grava licitações localmente
- usa apenas cache curto do Streamlit para reduzir chamadas repetidas
- exporta apenas o resultado visível da consulta atual

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Variáveis úteis

- `PNCP_PAGE_SIZE` — tamanho da página da API
- `PNCP_MAX_PAGES_PER_QUERY` — quantidade máxima de páginas por leitura
- `PNCP_DEFAULT_DAYS_BACK` — janela padrão de dias
- `PNCP_CACHE_TTL_SECONDS` — cache curto em memória
- `PNCP_CONNECT_TIMEOUT`
- `PNCP_READ_TIMEOUT`

## Observação

Este projeto depende da disponibilidade da API pública do PNCP. Se a API estiver indisponível, a interface informa a falha e não simula dados armazenados.
