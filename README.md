# Radar Suprema de Licitações

Produto Streamlit com **busca rápida sobre base própria** sincronizada do PNCP. A ideia central é simples: o usuário não fica esperando a API do PNCP na tela de busca. Primeiro a aplicação sincroniza uma janela real de dados; depois a pesquisa acontece no banco local, com score, filtros e alertas.

## O que este projeto já entrega
- sincronização real com `https://pncp.gov.br/api/consulta`;
- coleta da rota `/v1/contratacoes/proposta`;
- enriquecimento opcional com `/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}`;
- base SQLite local com índice FTS5;
- páginas focadas em uso operacional;
- alertas por perfil;
- exportação rápida em CSV;
- automação via GitHub Actions.

## Estrutura
```text
app.py
pages/
app/core/
app/services/
data/radar_suprema.db
.github/workflows/pncp_sync.yml
```

## Subindo no GitHub + Streamlit
1. Crie um repositório e envie todos os arquivos.
2. No Streamlit Community Cloud, aponte a entrada para `app.py`.
3. Instale dependências a partir de `requirements.txt`.
4. Rode a página **Operação PNCP** para fazer a primeira sincronização.

## Rodando localmente
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Sincronização manual pelo terminal
```bash
python -m app.services.sync_job
```

## Observações importantes
- Esta versão **não usa fallback**. Se não houver sincronização, a base ficará vazia até você coletar dados reais.
- A busca do usuário é feita sobre a base local para evitar timeout na tela.
- Em GitHub Actions, o banco `data/radar_suprema.db` é comitado de volta ao repositório após a coleta.

## Recomendação de operação
- faça sincronizações frequentes com janela curta;
- mantenha `with_details=true` quando quiser mais qualidade nos links e valores;
- use a página **Radar 360** para priorização rápida.
