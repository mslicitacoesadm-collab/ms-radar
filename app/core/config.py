from __future__ import annotations

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]
ASSETS_DIR = BASE_DIR / 'app' / 'assets'

PNCP_CONSULTA_BASE_URL = os.getenv('PNCP_CONSULTA_BASE_URL', 'https://pncp.gov.br/api/consulta')
REQUESTS_USER_AGENT = os.getenv('RADAR_USER_AGENT', 'Mozilla/5.0 (compatible; RadarEspelhoPNCP/6.0; +https://pncp.gov.br)')
PNCP_CONNECT_TIMEOUT = float(os.getenv('PNCP_CONNECT_TIMEOUT', '12'))
PNCP_READ_TIMEOUT = float(os.getenv('PNCP_READ_TIMEOUT', '45'))
PNCP_MAX_RETRIES = int(os.getenv('PNCP_MAX_RETRIES', '3'))
PNCP_RETRY_BACKOFF = float(os.getenv('PNCP_RETRY_BACKOFF', '1.2'))

# Modo espelho: consulta live, sem persistência local.
PNCP_PAGE_SIZE = max(10, min(100, int(os.getenv('PNCP_PAGE_SIZE', '20'))))
PNCP_MAX_PAGES_PER_QUERY = max(1, min(10, int(os.getenv('PNCP_MAX_PAGES_PER_QUERY', '3'))))
PNCP_DEFAULT_DAYS_BACK = max(1, min(30, int(os.getenv('PNCP_DEFAULT_DAYS_BACK', '7'))))
PNCP_CACHE_TTL_SECONDS = max(30, int(os.getenv('PNCP_CACHE_TTL_SECONDS', '90')))
PNCP_HOME_LIMIT = max(10, min(100, int(os.getenv('PNCP_HOME_LIMIT', '24'))))

MODALIDADES = {
    1: 'Leilão Eletrônico',
    2: 'Diálogo Competitivo',
    3: 'Concurso',
    4: 'Concorrência Eletrônica',
    5: 'Concorrência Presencial',
    6: 'Pregão Eletrônico',
    7: 'Pregão Presencial',
    8: 'Dispensa de Licitação',
    9: 'Inexigibilidade',
    10: 'Manifestação de Interesse',
    11: 'Pré-qualificação',
    12: 'Credenciamento',
    13: 'Leilão Presencial',
}

MODO_DISPUTA = {
    1: 'Aberto',
    2: 'Fechado',
    3: 'Aberto-Fechado',
    4: 'Dispensa Com Disputa',
    5: 'Não se aplica',
    6: 'Fechado-Aberto',
}

DEFAULT_MODALIDADES_SCAN = [6, 4, 8, 9, 7, 5, 3, 2, 1, 10, 11, 12, 13]
DEFAULT_UFS = [
    '', 'AC', 'AL', 'AM', 'AP', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MG', 'MS', 'MT',
    'PA', 'PB', 'PE', 'PI', 'PR', 'RJ', 'RN', 'RO', 'RR', 'RS', 'SC', 'SE', 'SP', 'TO'
]

NICHOS_PRONTOS = {
    'Combustíveis': ['combustivel', 'gasolina', 'diesel', 'etanol', 'lubrificante'],
    'Merenda e alimentos': ['merenda', 'alimento', 'generos alimenticios', 'polpa', 'cesta basica'],
    'Material gráfico': ['grafico', 'impressao', 'banner', 'cartaz', 'camiseta'],
    'Limpeza': ['limpeza', 'higiene', 'saneante', 'descartavel'],
    'Saúde': ['medicamento', 'hospitalar', 'saude', 'odontologico', 'laboratorial'],
    'TIC e software': ['software', 'licenca', 'informatica', 'ti', 'computador', 'impressora'],
    'Obras e engenharia': ['obra', 'engenharia', 'reforma', 'construcao', 'pavimentacao'],
    'Serviços terceirizados': ['terceirizacao', 'vigilancia', 'portaria', 'recepcao', 'copeiragem'],
}
