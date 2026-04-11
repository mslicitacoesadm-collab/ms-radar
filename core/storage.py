from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parents[1] / 'data' / 'ms_radar_access.db'


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_login_at TEXT DEFAULT CURRENT_TIMESTAMP,
                display_name TEXT
            )"""
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                external_reference TEXT UNIQUE,
                preapproval_id TEXT,
                plan_code TEXT,
                amount REAL,
                frequency INTEGER,
                frequency_type TEXT,
                checkout_url TEXT,
                status TEXT,
                payer_email TEXT,
                raw_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        conn.execute('CREATE INDEX IF NOT EXISTS idx_subscriptions_email ON subscriptions(email)')
        conn.commit()


@contextmanager
def get_conn():
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def upsert_user(email: str, display_name: Optional[str] = None) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO users(email, display_name) VALUES(?, ?)
               ON CONFLICT(email) DO UPDATE SET
                   last_login_at=CURRENT_TIMESTAMP,
                   display_name=COALESCE(excluded.display_name, users.display_name)
            """,
            (email.strip().lower(), display_name),
        )
        conn.commit()


def save_subscription(data: Dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO subscriptions(
                    email, external_reference, preapproval_id, plan_code, amount, frequency,
                    frequency_type, checkout_url, status, payer_email, raw_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(external_reference) DO UPDATE SET
                    preapproval_id=excluded.preapproval_id,
                    plan_code=excluded.plan_code,
                    amount=excluded.amount,
                    frequency=excluded.frequency,
                    frequency_type=excluded.frequency_type,
                    checkout_url=excluded.checkout_url,
                    status=excluded.status,
                    payer_email=excluded.payer_email,
                    raw_json=excluded.raw_json,
                    updated_at=CURRENT_TIMESTAMP
            """,
            (
                data.get('email', '').strip().lower(),
                data.get('external_reference'),
                data.get('preapproval_id'),
                data.get('plan_code'),
                data.get('amount'),
                data.get('frequency'),
                data.get('frequency_type'),
                data.get('checkout_url'),
                data.get('status'),
                data.get('payer_email'),
                data.get('raw_json'),
            ),
        )
        conn.commit()


def update_subscription_status(external_reference: str, status: str, preapproval_id: Optional[str] = None, raw_json: Optional[str] = None) -> None:
    with get_conn() as conn:
        conn.execute(
            """UPDATE subscriptions
               SET status=?,
                   preapproval_id=COALESCE(?, preapproval_id),
                   raw_json=COALESCE(?, raw_json),
                   updated_at=CURRENT_TIMESTAMP
               WHERE external_reference=?""",
            (status, preapproval_id, raw_json, external_reference),
        )
        conn.commit()


def list_subscriptions_by_email(email: str) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            'SELECT * FROM subscriptions WHERE email=? ORDER BY id DESC',
            (email.strip().lower(),),
        ).fetchall()
    return [dict(r) for r in rows]


def get_latest_active_subscription(email: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        row = conn.execute(
            """SELECT * FROM subscriptions
               WHERE email=? AND lower(coalesce(status,'')) IN ('authorized','active')
               ORDER BY id DESC LIMIT 1""",
            (email.strip().lower(),),
        ).fetchone()
    return dict(row) if row else None
