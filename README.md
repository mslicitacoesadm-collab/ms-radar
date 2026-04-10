# Radar Suprema de Licitações

Sistema profissional de busca e alerta sobre base própria do PNCP, com arquitetura separada em duas etapas:

1. **Coleta resumida** das contratações com proposta aberta.
2. **Enriquecimento posterior** do detalhe da contratação.

Esse desenho reduz o risco de timeout e melhora a experiência de quem busca rapidamente oportunidades reais.

## Como rodar localmente

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Variáveis opcionais

```bash
PNCP_BASE_URL=https://pncp.gov.br/api/consulta
PNCP_CONNECT_TIMEOUT=5
PNCP_READ_TIMEOUT=60
PNCP_MAX_RETRIES=4
PNCP_RETRY_BACKOFF=1.2
PNCP_DEFAULT_PAGE_SIZE=20
PNCP_DETAIL_BATCH_SIZE=40
RADAR_DB_PATH=data/radar_suprema.db
RADAR_USER_AGENT=RadarSuprema/2.0
```

## Fluxo recomendado

- Abra **Operação PNCP**.
- Clique em **Testar conexão com o PNCP**.
- Execute **Sincronizar resumos agora**.
- Em seguida, rode **Enriquecer detalhes pendentes** em lotes menores.
- Use a base já indexada na **Busca Suprema** e no **Radar 360**.

## GitHub Actions

O workflow incluído executa coleta resumida. Se quiser também enriquecer detalhes, acrescente uma segunda chamada ao job.
