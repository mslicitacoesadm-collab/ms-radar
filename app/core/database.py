from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from .config import DB_PATH, DATA_DIR

DATA_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS notices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    object_text TEXT,
    agency TEXT,
    state TEXT,
    city TEXT,
    modality TEXT,
    estimated_value REAL DEFAULT 0,
    publication_date TEXT,
    deadline_date TEXT,
    source_url TEXT,
    source_system TEXT,
    raw_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    keywords TEXT,
    state TEXT,
    city TEXT,
    modality TEXT,
    min_value REAL DEFAULT 0,
    max_value REAL DEFAULT 0,
    email TEXT,
    telegram_chat_id TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alert_deliveries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    source_id TEXT NOT NULL,
    delivered_via TEXT NOT NULL,
    delivered_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(alert_id, source_id, delivered_via)
);

CREATE TABLE IF NOT EXISTS sync_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mode TEXT,
    query_used TEXT,
    items_found INTEGER DEFAULT 0,
    items_inserted INTEGER DEFAULT 0,
    status TEXT,
    details TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA)


def upsert_notices(rows: Iterable[Dict]) -> Tuple[int, int]:
    inserted = 0
    found = 0
    sql = """
    INSERT INTO notices (
        source_id, title, object_text, agency, state, city, modality,
        estimated_value, publication_date, deadline_date, source_url,
        source_system, raw_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        source_url=excluded.source_url,
        source_system=excluded.source_system,
        raw_json=excluded.raw_json,
        updated_at=CURRENT_TIMESTAMP
    """
    with get_conn() as conn:
        for row in rows:
            found += 1
            cur = conn.execute("SELECT 1 FROM notices WHERE source_id=?", (row["source_id"],))
            exists = cur.fetchone() is not None
            conn.execute(
                sql,
                (
                    row.get("source_id"),
                    row.get("title"),
                    row.get("object_text"),
                    row.get("agency"),
                    row.get("state"),
                    row.get("city"),
                    row.get("modality"),
                    float(row.get("estimated_value") or 0),
                    row.get("publication_date"),
                    row.get("deadline_date"),
                    row.get("source_url"),
                    row.get("source_system", "PNCP"),
                    json.dumps(row, ensure_ascii=False),
                ),
            )
            if not exists:
                inserted += 1
    return found, inserted


def list_notices(limit: int = 500) -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute(
            """
            SELECT * FROM notices
            ORDER BY COALESCE(deadline_date, publication_date) DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return cur.fetchall()


def list_states() -> List[str]:
    with get_conn() as conn:
        cur = conn.execute("SELECT DISTINCT state FROM notices WHERE TRIM(COALESCE(state,''))<>'' ORDER BY state")
        return [row[0] for row in cur.fetchall()]


def list_modalities() -> List[str]:
    with get_conn() as conn:
        cur = conn.execute("SELECT DISTINCT modality FROM notices WHERE TRIM(COALESCE(modality,''))<>'' ORDER BY modality")
        return [row[0] for row in cur.fetchall()]


def save_alert(payload: Dict) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO alerts (name, keywords, state, city, modality, min_value, max_value, email, telegram_chat_id, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.get("name"),
                payload.get("keywords", ""),
                payload.get("state", ""),
                payload.get("city", ""),
                payload.get("modality", ""),
                float(payload.get("min_value") or 0),
                float(payload.get("max_value") or 0),
                payload.get("email", ""),
                payload.get("telegram_chat_id", ""),
                int(payload.get("is_active", 1)),
            ),
        )
        return int(cur.lastrowid)


def list_alerts() -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM alerts ORDER BY id DESC")
        return cur.fetchall()


def delete_alert(alert_id: int) -> None:
    with get_conn() as conn:
        conn.execute("DELETE FROM alerts WHERE id=?", (alert_id,))


def log_sync(mode: str, query_used: str, items_found: int, items_inserted: int, status: str, details: str = "") -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO sync_runs (mode, query_used, items_found, items_inserted, status, details) VALUES (?, ?, ?, ?, ?, ?)",
            (mode, query_used, items_found, items_inserted, status, details),
        )


def list_sync_runs(limit: int = 20) -> List[sqlite3.Row]:
    with get_conn() as conn:
        cur = conn.execute("SELECT * FROM sync_runs ORDER BY id DESC LIMIT ?", (limit,))
        return cur.fetchall()


def delivery_exists(alert_id: int, source_id: str, channel: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "SELECT 1 FROM alert_deliveries WHERE alert_id=? AND source_id=? AND delivered_via=?",
            (alert_id, source_id, channel),
        )
        return cur.fetchone() is not None


def register_delivery(alert_id: int, source_id: str, channel: str) -> None:
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO alert_deliveries (alert_id, source_id, delivered_via) VALUES (?, ?, ?)",
            (alert_id, source_id, channel),
        )


def get_metrics() -> Dict[str, int]:
    with get_conn() as conn:
        notices = conn.execute("SELECT COUNT(*) FROM notices").fetchone()[0]
        alerts = conn.execute("SELECT COUNT(*) FROM alerts WHERE is_active=1").fetchone()[0]
        agencies = conn.execute("SELECT COUNT(DISTINCT agency) FROM notices").fetchone()[0]
        states = conn.execute("SELECT COUNT(DISTINCT state) FROM notices WHERE TRIM(COALESCE(state,''))<>''").fetchone()[0]
        return {
            "notices": notices,
            "alerts": alerts,
            "agencies": agencies,
            "states": states,
        }

