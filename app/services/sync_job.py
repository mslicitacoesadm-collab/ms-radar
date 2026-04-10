from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.core.database import Database
from app.core.pncp_client import PNCPClient, PNCPClientError
from app.core.search_engine import apply_detail, normalize_summary_item


def sync_open_opportunities(
    *,
    days_ahead: int = 3,
    max_pages: int = 20,
    page_size: int = 50,
    with_details: bool = True,
) -> dict[str, Any]:
    db = Database()
    client = PNCPClient()
    run_id = db.create_sync_run('PNCP_OPEN', details=f'days_ahead={days_ahead};max_pages={max_pages};page_size={page_size}')
    imported = updated = seen = 0
    try:
        rows: list[dict[str, Any]] = []
        for offset in range(0, days_ahead + 1):
            data_final = (date.today() + timedelta(days=offset)).isoformat()
            for pagina in range(1, max_pages + 1):
                payload = client.list_open_opportunities(data_final=data_final, pagina=pagina, tamanho_pagina=page_size)
                items = payload.get('data', []) if isinstance(payload, dict) else []
                if not items:
                    break
                for item in items:
                    seen += 1
                    row = normalize_summary_item(item, 'proposta_aberta', data_final)
                    if with_details and row.get('orgao_cnpj') and row.get('ano_compra') and row.get('sequencial_compra'):
                        try:
                            detail = client.get_opportunity_detail(
                                cnpj=row['orgao_cnpj'],
                                ano=int(row['ano_compra']),
                                sequencial=int(row['sequencial_compra']),
                            )
                            if isinstance(detail, dict):
                                row = apply_detail(row, detail)
                        except Exception:
                            pass
                    if row['numero_controle_pncp']:
                        rows.append(row)
                total_paginas = int(payload.get('totalPaginas') or 0)
                if total_paginas and pagina >= total_paginas:
                    break
        imported, updated = db.upsert_opportunities(rows)
        db.finish_sync_run(run_id, 'success', imported, updated, seen, details=f'rows={len(rows)}')
        return {'status': 'success', 'imported': imported, 'updated': updated, 'seen': seen}
    except PNCPClientError as exc:
        db.finish_sync_run(run_id, 'error', imported, updated, seen, details=str(exc))
        raise


if __name__ == '__main__':
    result = sync_open_opportunities()
    print(result)
