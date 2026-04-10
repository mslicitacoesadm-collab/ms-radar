from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

from .config import DB_PATH, DATA_DIR
from .models import Notice


SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_id TEXT UNIQUE,
        title TEXT NOT NULL,
        object_text TEXT NOT NULL,
        agency TEXT,
        state TEXT,
        city TEXT,
        modality TEXT,
        estimated_value REAL DEFAULT 0,
        publication_date TEXT,
        deadline_date TEXT,
        opening_date TEXT,
        situation TEXT,
        source_url TEXT,
        source_system TEXT,
        pncp_cnpj TEXT,
        pncp_ano INTEGER DEFAULT 0,
        pncp_sequencial INTEGER DEFAULT 0,
        raw_json TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS alert_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        keywords TEXT,
        state TEXT,
        city TEXT,
        modality TEXT,
        min_value REAL DEFAULT 0,
        email TEXT,
        telegram_chat_id TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sync_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        origin TEXT NOT NULL,
        total_imported INTEGER DEFAULT 0,
        status TEXT NOT NULL,
        details TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS delivery_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        alert_profile_id INTEGER,
        notice_source_id TEXT,
        channel TEXT,
        status TEXT,
        details TEXT,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS saved_views (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        query_json TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """,
]


def ensure_database() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        for ddl in SCHEMA:
            conn.execute(ddl)
        conn.commit()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    ensure_database()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert_notices(notices: Iterable[Notice]) -> int:
    now = datetime.utcnow().isoformat(timespec='seconds')
    count = 0
    with get_conn() as conn:
        for n in notices:
            conn.execute(
                """
                INSERT INTO notices (
                    source_id,title,object_text,agency,state,city,modality,estimated_value,
                    publication_date,deadline_date,opening_date,situation,source_url,source_system,
                    pncp_cnpj,pncp_ano,pncp_sequencial,raw_json,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET
                    title=excluded.title,
                    object_text=excluded.object_text,
                    agency=excluded.agency,
                    state=excluded.state,
                    city=excluded.city,
                    modality=excluded.modality,
                    estimated_value=excluded.estimated_value,
                    publication_date=excluded.publication_date,
                    deadline_date=excluded.deadline_date,
                    opening_date=excluded.opening_date,
                    situation=excluded.situation,
                    source_url=excluded.source_url,
                    source_system=excluded.source_system,
                    pncp_cnpj=excluded.pncp_cnpj,
                    pncp_ano=excluded.pncp_ano,
                    pncp_sequencial=excluded.pncp_sequencial,
                    raw_json=excluded.raw_json,
                    updated_at=excluded.updated_at
                """,
                (
                    n.source_id,
                    n.title,
                    n.object_text,
                    n.agency,
                    n.state,
                    n.city,
                    n.modality,
                    float(n.estimated_value or 0),
                    n.publication_date,
                    n.deadline_date,
                    n.opening_date,
                    n.situation,
                    n.source_url,
                    n.source_system,
                    n.pncp_cnpj,
                    int(n.pncp_ano or 0),
                    int(n.pncp_sequencial or 0),
                    n.raw_json or json.dumps(n.__dict__, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            count += 1
    return count


def query_df(sql: str, params: tuple = ()):  # lazy import for streamlit performance
    import pandas as pd
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def insert_sync_history(origin: str, total_imported: int, status: str, details: str = '') -> None:
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO sync_history (origin,total_imported,status,details,created_at) VALUES (?,?,?,?,?)',
            (origin, total_imported, status, details, datetime.utcnow().isoformat(timespec='seconds')),
        )


def create_alert_profile(data: dict) -> None:
    now = datetime.utcnow().isoformat(timespec='seconds')
    with get_conn() as conn:
        conn.execute(
            '''
            INSERT INTO alert_profiles (name,keywords,state,city,modality,min_value,email,telegram_chat_id,active,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            ''',
            (
                data.get('name', ''),
                data.get('keywords', ''),
                data.get('state', ''),
                data.get('city', ''),
                data.get('modality', ''),
                float(data.get('min_value', 0) or 0),
                data.get('email', ''),
                data.get('telegram_chat_id', ''),
                1 if data.get('active', True) else 0,
                now,
                now,
            ),
        )


def log_delivery(alert_profile_id: int, notice_source_id: str, channel: str, status: str, details: str = '') -> None:
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO delivery_log (alert_profile_id,notice_source_id,channel,status,details,created_at) VALUES (?,?,?,?,?,?)',
            (alert_profile_id, notice_source_id, channel, status, details, datetime.utcnow().isoformat(timespec='seconds')),
        )


def save_view(name: str, query_json: str) -> None:
    with get_conn() as conn:
        conn.execute(
            'INSERT INTO saved_views (name,query_json,created_at) VALUES (?,?,?)',
            (name, query_json, datetime.utcnow().isoformat(timespec='seconds')),
        )
