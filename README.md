# Radar Suprema de Licitações

Sistema profissional de busca e alerta com **coleta híbrida do PNCP**:

- **API oficial** do PNCP como fonte principal.
- **Scraping público** do portal como apoio quando a API estiver instável.
- **Base própria local** para garantir busca rápida e estável.

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Variáveis opcionais

```bash
PNCP_BASE_URL=https://pncp.gov.br/api/consulta
PNCP_PORTAL_BASE_URL=https://pncp.gov.br
PNCP_CONNECT_TIMEOUT=8
PNCP_READ_TIMEOUT=45
PNCP_MAX_RETRIES=3
PNCP_RETRY_BACKOFF=1.1
PNCP_DEFAULT_PAGE_SIZE=20
PNCP_DETAIL_BATCH_SIZE=25
PNCP_SOURCE_MODE=hybrid
RADAR_DB_PATH=data/radar_suprema.db
RADAR_USER_AGENT=RadarSuprema/4.0
```

## Por que a versão anterior falhava

O teste usava tamanho de página menor que o mínimo aceito pela API. Agora o sistema respeita o mínimo de **10** itens por página e a coleta pode alternar entre **API** e **scraping**.

## Fluxo recomendado

1. Abra **Operação PNCP**.
2. Clique em **Testar conexão com o PNCP**.
3. Execute **Sincronizar base real agora**.
4. Em seguida, rode **Enriquecer detalhes pendentes** em lotes menores.
5. Pesquise e filtre na base local sem depender da resposta ao vivo do PNCP.

## Observação importante

O scraper é um apoio técnico sobre páginas públicas do portal. Se o HTML do PNCP mudar, talvez seja necessário ajustar os seletores e heurísticas de extração.
