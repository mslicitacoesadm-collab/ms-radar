from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv('RADAR_DB_PATH', DATA_DIR / 'radar_suprema.db'))
PNCP_BASE_URL = os.getenv('PNCP_BASE_URL', 'https://pncp.gov.br/api/consulta')
PNCP_PORTAL_BASE_URL = os.getenv('PNCP_PORTAL_BASE_URL', 'https://pncp.gov.br')
REQUESTS_USER_AGENT = os.getenv('RADAR_USER_AGENT', 'Mozilla/5.0 (compatible; RadarSuprema/4.0; +https://pncp.gov.br)')

PNCP_CONNECT_TIMEOUT = float(os.getenv('PNCP_CONNECT_TIMEOUT', '8'))
PNCP_READ_TIMEOUT = float(os.getenv('PNCP_READ_TIMEOUT', '45'))
PNCP_MAX_RETRIES = int(os.getenv('PNCP_MAX_RETRIES', '3'))
PNCP_RETRY_BACKOFF = float(os.getenv('PNCP_RETRY_BACKOFF', '1.1'))
PNCP_DEFAULT_PAGE_SIZE = max(10, int(os.getenv('PNCP_DEFAULT_PAGE_SIZE', '20')))
PNCP_DETAIL_BATCH_SIZE = max(5, int(os.getenv('PNCP_DETAIL_BATCH_SIZE', '25')))
PNCP_SOURCE_MODE = os.getenv('PNCP_SOURCE_MODE', 'hybrid').lower()
SCRAPER_MAX_PAGES = max(1, int(os.getenv('SCRAPER_MAX_PAGES', '10')))

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


@dataclass(frozen=True)
class SyncWindow:
    max_pages: int = 20
    page_size: int = PNCP_DEFAULT_PAGE_SIZE
    detail_batch_size: int = PNCP_DETAIL_BATCH_SIZE
