from __future__ import annotations

import argparse
import json

from app.core.alerts import process_alerts
from app.core.config import load_settings
from app.core.database import init_db, list_alerts, list_notices, log_sync, upsert_notices
from app.core.pncp_client import PNCPClient



def run_sync(query: str = "", days: int = 30) -> dict:
    init_db()
    client = PNCPClient()
    settings = load_settings()

    notices = client.search(query=query, days=days)
    found, inserted = upsert_notices(notices)

    alerts = [dict(row) for row in list_alerts()]
    deliveries = process_alerts(alerts, notices)

    mode = "api" if settings.pncp_search_url else "sample"
    log_sync(mode=mode, query_used=query, items_found=found, items_inserted=inserted, status="ok", details=f"deliveries={len(deliveries)}")

    return {
        "mode": mode,
        "found": found,
        "inserted": inserted,
        "deliveries": len(deliveries),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sincronização do Radar de Licitações")
    parser.add_argument("--query", default="", help="Consulta base")
    parser.add_argument("--days", default=30, type=int, help="Janela em dias")
    args = parser.parse_args()
    result = run_sync(query=args.query, days=args.days)
    print(json.dumps(result, ensure_ascii=False, indent=2))
