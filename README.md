# MS Radar V10 — assinatura recorrente com Mercado Pago

Esta versão mantém o **PNCP em modo espelho** e cria uma camada separada para **acesso recorrente**:

- **Não armazena licitações em banco**.
- Usa persistência mínima **apenas para usuários e assinaturas**.
- Faz a cobrança recorrente pelo **Mercado Pago**.
- Libera o acesso premium automaticamente ao retornar do checkout ou ao validar o e-mail novamente.

## Estrutura

- `app.py` — app Streamlit principal.
- `core/pncp.py` — leitura rápida do PNCP e vitrine.
- `core/mercadopago.py` — integração de assinaturas recorrentes.
- `core/storage.py` — banco SQLite leve só para usuários/assinaturas.
- `core/access.py` — regras de monetização.
- `webhook_server.py` — webhook opcional em FastAPI.

## Como configurar

### 1) Instale dependências

```bash
pip install -r requirements.txt
```

### 2) Configure as variáveis

No Streamlit Cloud, use **Secrets**. Localmente, use variáveis de ambiente.

```toml
MP_ACCESS_TOKEN = "SEU_ACCESS_TOKEN_DO_MERCADO_PAGO"
PUBLIC_APP_URL = "https://SEU-APP.streamlit.app"
```

> `PUBLIC_APP_URL` precisa apontar para a URL pública exata do seu app, porque ela é usada como `back_url` da assinatura.

### 3) Rode o app

```bash
streamlit run app.py
```

## Como o fluxo funciona

1. O visitante entra e já vê a vitrine rápida do PNCP.
2. Ele informa o e-mail.
3. Escolhe um plano recorrente.
4. O app cria uma assinatura no Mercado Pago e abre o checkout.
5. Ao retornar, o app valida o status automaticamente.
6. Se a assinatura estiver ativa/autorizada, o plano premium é liberado.

## Observações importantes

- O app **não usa banco de dados para guardar licitações**.
- O SQLite local guarda somente o mínimo para assinaturas e reconciliação.
- O webhook é opcional. O app já funciona sem ele porque também reconcilia a assinatura quando o usuário volta ao sistema.
- Para produção mais robusta, você pode mover a camada de assinaturas para um banco externo leve.
