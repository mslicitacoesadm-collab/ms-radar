from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "radar_licitacoes.db"
SAMPLE_JSON_PATH = BASE_DIR / "app" / "assets" / "sample_notices.json"


def _read_streamlit_secrets() -> Dict[str, Any]:
    try:
        import streamlit as st  # type: ignore
        return dict(st.secrets)
    except Exception:
        return {}


@dataclass(frozen=True)
class Settings:
    pncp_search_url: str = ""
    pncp_timeout: int = 25
    sync_sample_if_empty: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    app_base_url: str = ""



def load_settings() -> Settings:
    secrets = _read_streamlit_secrets()

    def pick(name: str, default: Any) -> Any:
        return secrets.get(name, os.getenv(name, default))

    return Settings(
        pncp_search_url=str(pick("PNCP_SEARCH_URL", "")).strip(),
        pncp_timeout=int(pick("PNCP_TIMEOUT", 25)),
        sync_sample_if_empty=str(pick("SYNC_SAMPLE_IF_EMPTY", "true")).lower() in {"1", "true", "yes", "sim"},
        smtp_host=str(pick("SMTP_HOST", "")).strip(),
        smtp_port=int(pick("SMTP_PORT", 587)),
        smtp_user=str(pick("SMTP_USER", "")).strip(),
        smtp_password=str(pick("SMTP_PASSWORD", "")).strip(),
        smtp_from=str(pick("SMTP_FROM", "")).strip(),
        telegram_bot_token=str(pick("TELEGRAM_BOT_TOKEN", "")).strip(),
        telegram_chat_id=str(pick("TELEGRAM_CHAT_ID", "")).strip(),
        app_base_url=str(pick("APP_BASE_URL", "")).strip(),
    )

