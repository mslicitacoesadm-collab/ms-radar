# Radar Suprema Live

Sistema profissional de busca e alerta de licitações com **base própria local**.

## Ideia central
O usuário **não pesquisa diretamente no PNCP**. O sistema sincroniza os dados do PNCP em segundo plano e grava tudo em SQLite. A pesquisa, o radar e os alertas trabalham em cima dessa base local.

## O que esta versão faz
- coleta real do PNCP pela API pública de consultas;
- sincronização de **publicações recentes**;
- sincronização de **propostas abertas**;
- enriquecimento de detalhes por lote;
- busca local indexada por FTS5;
- radar diário;
- alertas por nicho, região e valor;
- workflow do GitHub Actions para manter a base viva.

## Variáveis importantes
- `PNCP_CONSULTA_BASE_URL=https://pncp.gov.br/api/consulta`
- `RADAR_DB_PATH=data/radar_suprema_live.db`
- `PNCP_CONNECT_TIMEOUT=10`
- `PNCP_READ_TIMEOUT=60`
- `PNCP_PAGE_SIZE=20`
- `PNCP_MAX_PAGES_PER_QUERY=8`
- `PNCP_QUICK_SYNC_DAYS=2`
- `PNCP_DETAIL_BATCH_SIZE=20`

## Como subir no Streamlit Cloud
1. Suba este projeto para o GitHub.
2. No Streamlit, aponte o app principal para `app.py`.
3. Em *Secrets*, informe pelo menos:
   - `PNCP_CONSULTA_BASE_URL="https://pncp.gov.br/api/consulta"`
   - `RADAR_DB_PATH="data/radar_suprema_live.db"`
4. Ative o GitHub Actions no repositório.
5. Rode o workflow manualmente na primeira vez.

## Comandos locais
```bash
python -m app.services.sync_job probe
python -m app.services.sync_job quick
python -m app.services.sync_job detalhe
streamlit run app.py
```

## Estratégia recomendada
- **GitHub Actions** alimenta a base a cada 15 minutos.
- **Streamlit** entrega a interface.
- O usuário final pesquisa sem ficar aguardando resposta do portal.
