# MS Radar V10.1 Clean

Versão reconstruída para teste operacional, com interface mais leve, simples e profissional.

## O que esta versão faz
- consulta o PNCP em tempo real pelo endpoint de propostas abertas
- usa poucas chamadas para manter a entrada rápida
- mostra navegação principal na própria página
- oferece recorte por estado, cidade, modalidade e filtro avançado
- entra em modo demonstração automaticamente quando o PNCP estiver indisponível

## Como rodar
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Observações
- não há integração de pagamento nesta versão
- não há banco persistente de licitações
- a tela usa vitrine leve para priorizar velocidade e clareza
