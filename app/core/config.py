from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / 'data'
ASSETS_DIR = BASE_DIR / 'app' / 'assets'
DB_PATH = DATA_DIR / 'radar_licitacoes.db'


@dataclass(frozen=True)
class Settings:
    pncp_base_url: str = os.getenv('PNCP_SEARCH_URL', 'https://pncp.gov.br/api/consulta').rstrip('/')
    pncp_timeout: int = int(os.getenv('PNCP_TIMEOUT', '25'))
    smtp_host: str = os.getenv('SMTP_HOST', '')
    smtp_port: int = int(os.getenv('SMTP_PORT', '587'))
    smtp_user: str = os.getenv('SMTP_USER', '')
    smtp_password: str = os.getenv('SMTP_PASSWORD', '')
    smtp_from: str = os.getenv('SMTP_FROM', '')
    telegram_bot_token: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    telegram_chat_id: str = os.getenv('TELEGRAM_CHAT_ID', '')

    @property
    def alerts_ready(self) -> bool:
        return bool((self.smtp_host and self.smtp_user and self.smtp_password and self.smtp_from) or (self.telegram_bot_token and self.telegram_chat_id))


SETTINGS = Settings()
