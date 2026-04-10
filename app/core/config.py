from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.getenv('RADAR_DB_PATH', DATA_DIR / 'radar_suprema.db'))
PNCP_BASE_URL = os.getenv('PNCP_BASE_URL', 'https://pncp.gov.br/api/consulta')
DEFAULT_TIMEOUT = int(os.getenv('PNCP_TIMEOUT', '20'))
REQUESTS_USER_AGENT = os.getenv('RADAR_USER_AGENT', 'RadarSuprema/1.0')


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


@dataclass(frozen=True)
class SyncWindow:
    days_back: int = 3
    max_pages: int = 50
    page_size: int = 50
