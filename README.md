# MS Radar V10.1 Funcional Clean

Versão reconstruída para teste real, com foco em velocidade, simplicidade e utilidade.

## O que mudou

- Removido Mercado Pago nesta versão de teste.
- Removido banco de licitações.
- Corrigido formato de datas para a API do PNCP: `AAAAMMDD`.
- Home leve: consulta automática com poucas chamadas paralelas.
- Cache temporário de 120 segundos para não travar a navegação.
- Filtro avançado sob demanda.
- Paginação minimalista.
- Interface limpa, sem menu lateral como eixo principal.

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Observações técnicas

Esta versão usa a API pública do PNCP como fonte principal:

- `https://pncp.gov.br/api/consulta/v1/contratacoes/proposta`
- `https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao`

A raspagem direta do front-end do PNCP não foi adotada como principal porque o portal é dinâmico e pode quebrar com alterações de HTML/JavaScript. A API é a rota mais estável para produto.

## Configurações opcionais

Você pode mudar a base da API por variável de ambiente:

```bash
PNCP_BASE=https://pncp.gov.br/api/consulta
```

## Filosofia do projeto

O MS Radar funciona como espelho: busca, normaliza e exibe. Não armazena licitações.
