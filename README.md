# MS Radar V8 revisada

Esta é a versão V8 revisada do MS Radar, com foco em:

- **modo espelho do PNCP**
- **sem banco persistente de licitações**
- **home comercial rápida**
- **monetização leve por prévia gratuita**
- **simulação de desbloqueio premium na sessão**

## Estrutura

- `app.py` — app principal do Streamlit
- `core/pncp.py` — leitura rápida do PNCP e renderização
- `core/monetizacao.py` — lógica da prévia gratuita e desbloqueio premium na sessão
- `assets/logo_ms_radar.png` — logo da marca

## Como rodar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## O que foi revisado

- remoção de dependências desnecessárias para esta etapa
- preservação da home rápida
- prévia gratuita com bloqueio leve revisada
- exportação respeitando o plano atual
- navegação concentrada na página principal

## Observação

Nesta V8 revisada, o premium é **simulado na própria sessão** apenas para validação comercial e de usabilidade. A cobrança real ficou para as versões seguintes.
