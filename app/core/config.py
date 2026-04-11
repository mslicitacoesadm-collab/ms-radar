from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv('RADAR_DB_PATH', DATA_DIR / 'radar_suprema_live.db'))

# Consulta pública do PNCP
PNCP_CONSULTA_BASE_URL = os.getenv('PNCP_CONSULTA_BASE_URL', 'https://pncp.gov.br/api/consulta')
REQUESTS_USER_AGENT = os.getenv('RADAR_USER_AGENT', 'Mozilla/5.0 (compatible; RadarSupremaLive/5.0; +https://pncp.gov.br)')
PNCP_CONNECT_TIMEOUT = float(os.getenv('PNCP_CONNECT_TIMEOUT', '10'))
PNCP_READ_TIMEOUT = float(os.getenv('PNCP_READ_TIMEOUT', '60'))
PNCP_MAX_RETRIES = int(os.getenv('PNCP_MAX_RETRIES', '4'))
PNCP_RETRY_BACKOFF = float(os.getenv('PNCP_RETRY_BACKOFF', '1.5'))
PNCP_PAGE_SIZE = max(10, min(100, int(os.getenv('PNCP_PAGE_SIZE', '20'))))
PNCP_DETAIL_BATCH_SIZE = max(5, int(os.getenv('PNCP_DETAIL_BATCH_SIZE', '20')))
PNCP_QUICK_SYNC_DAYS = max(1, int(os.getenv('PNCP_QUICK_SYNC_DAYS', '2')))
PNCP_MAX_PAGES_PER_QUERY = max(1, int(os.getenv('PNCP_MAX_PAGES_PER_QUERY', '8')))
PNCP_GITHUB_SYNC_MODE = os.getenv('PNCP_GITHUB_SYNC_MODE', 'quick').lower()  # quick | full

MODALIDADES = {
    1: 'Leilão - Eletrônico',
    2: 'Diálogo Competitivo',
    3: 'Concurso',
    4: 'Concorrência - Eletrônica',
    5: 'Concorrência - Presencial',
    6: 'Pregão - Eletrônico',
    7: 'Pregão - Presencial',
    8: 'Dispensa de Licitação',
    9: 'Inexigibilidade',
    10: 'Manifestação de Interesse',
    11: 'Pré-qualificação',
    12: 'Credenciamento',
    13: 'Leilão - Presencial',
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


@dataclass(frozen=True)
class SyncWindow:
    max_pages: int = PNCP_MAX_PAGES_PER_QUERY
    page_size: int = PNCP_PAGE_SIZE
    detail_batch_size: int = PNCP_DETAIL_BATCH_SIZE
