from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Iterable
import sys

from app.core.config import DEFAULT_MODALIDADES_SCAN, PNCP_DETAIL_BATCH_SIZE, PNCP_MAX_PAGES_PER_QUERY, PNCP_PAGE_SIZE, PNCP_QUICK_SYNC_DAYS
from app.core.database import Database
from app.core.pncp_client import PNCPClient, PNCPClientError
from app.core.search_engine import apply_detail, normalize_summary_item
from app.core.utils import daterange_days, pncp_date


client = PNCPClient()


def probe_pncp_connection() -> dict[str, Any]:
    result = client.probe()
    return {
        'ok': result.ok,
        'status_code': result.status_code,
        'elapsed_seconds': result.elapsed_seconds,
        'message': result.message,
    }



def _ingest_payload(db: Database, payload: dict[str, Any], endpoint: str, fonte_data_referencia: str) -> tuple[int, int, int]:
    items = payload.get('data', []) or []
    rows = []
    seen = 0
    for item in items:
        row = normalize_summary_item(item, endpoint=endpoint, fonte_data_referencia=fonte_data_referencia)
        if row['numero_controle_pncp']:
            rows.append(row)
            seen += 1
    if not rows:
        return 0, 0, 0
    imported, updated = db.upsert_opportunities(rows, detail_status='summary')
    return seen, imported, updated



def sync_publications(days_back: int = PNCP_QUICK_SYNC_DAYS, max_pages: int = PNCP_MAX_PAGES_PER_QUERY, page_size: int = PNCP_PAGE_SIZE) -> dict[str, Any]:
    db = Database()
    data_inicial, data_final = daterange_days(days_back)
    run_id = db.create_sync_run('PNCP_PUBLICACAO', f'de={data_inicial};ate={data_final};pages={max_pages};page_size={page_size}')
    total_seen = total_imported = total_updated = 0
    errors: list[str] = []
    try:
        for modalidade in DEFAULT_MODALIDADES_SCAN:
            for pagina in range(1, max_pages + 1):
                try:
                    payload = client.list_published(
                        data_inicial=data_inicial,
                        data_final=data_final,
                        codigo_modalidade=modalidade,
                        pagina=pagina,
                        tamanho_pagina=page_size,
                    )
                except PNCPClientError as exc:
                    errors.append(f'publicacao modalidade={modalidade} pagina={pagina}: {exc}')
                    break
                seen, imported, updated = _ingest_payload(db, payload, 'publicacao', data_final)
                total_seen += seen
                total_imported += imported
                total_updated += updated
                if not payload.get('data'):
                    break
                total_paginas = int(payload.get('totalPaginas') or 0)
                if total_paginas and pagina >= total_paginas:
                    break
        status = 'success' if not errors else ('partial' if total_seen > 0 else 'error')
        db.finish_sync_run(run_id, status, total_imported, total_updated, total_seen, '\n'.join(errors[:30]))
        db.set_state('last_publication_sync', date.today().isoformat())
        return {'status': status, 'seen': total_seen, 'imported': total_imported, 'updated': total_updated, 'errors': errors}
    except Exception as exc:
        db.finish_sync_run(run_id, 'error', total_imported, total_updated, total_seen, str(exc))
        raise



def sync_open_proposals(max_pages: int = 3, page_size: int = PNCP_PAGE_SIZE) -> dict[str, Any]:
    db = Database()
    data_final = pncp_date(date.today())
    run_id = db.create_sync_run('PNCP_PROPOSTA_ABERTA', f'ate={data_final};pages={max_pages};page_size={page_size}')
    total_seen = total_imported = total_updated = 0
    errors: list[str] = []
    try:
        for modalidade in DEFAULT_MODALIDADES_SCAN:
            for pagina in range(1, max_pages + 1):
                try:
                    payload = client.list_open_proposals(
                        data_final=data_final,
                        codigo_modalidade=modalidade,
                        pagina=pagina,
                        tamanho_pagina=page_size,
                    )
                except PNCPClientError as exc:
                    errors.append(f'proposta modalidade={modalidade} pagina={pagina}: {exc}')
                    break
                seen, imported, updated = _ingest_payload(db, payload, 'proposta', data_final)
                total_seen += seen
                total_imported += imported
                total_updated += updated
                if not payload.get('data'):
                    break
                total_paginas = int(payload.get('totalPaginas') or 0)
                if total_paginas and pagina >= total_paginas:
                    break
        status = 'success' if not errors else ('partial' if total_seen > 0 else 'error')
        db.finish_sync_run(run_id, status, total_imported, total_updated, total_seen, '\n'.join(errors[:30]))
        db.set_state('last_open_sync', date.today().isoformat())
        return {'status': status, 'seen': total_seen, 'imported': total_imported, 'updated': total_updated, 'errors': errors}
    except Exception as exc:
        db.finish_sync_run(run_id, 'error', total_imported, total_updated, total_seen, str(exc))
        raise



def sync_quick() -> dict[str, Any]:
    pub = sync_publications(days_back=PNCP_QUICK_SYNC_DAYS, max_pages=PNCP_MAX_PAGES_PER_QUERY, page_size=PNCP_PAGE_SIZE)
    open_ = sync_open_proposals(max_pages=max(2, min(4, PNCP_MAX_PAGES_PER_QUERY // 2 or 2)), page_size=PNCP_PAGE_SIZE)
    return {
        'status': 'success' if pub['status'] == open_['status'] == 'success' else 'partial',
        'publication': pub,
        'open': open_,
    }



def enrich_pending_details(batch_size: int = PNCP_DETAIL_BATCH_SIZE) -> dict[str, Any]:
    db = Database()
    run_id = db.create_sync_run('PNCP_DETALHE', f'batch_size={batch_size}')
    processed = success = failed = 0
    errors: list[str] = []
    try:
        rows = db.pending_detail_candidates(limit=batch_size)
        for item in rows:
            processed += 1
            control = item['numero_controle_pncp']
            try:
                detail = client.get_opportunity_detail(cnpj=item['orgao_cnpj'], ano=int(item['ano_compra']), sequencial=int(item['sequencial_compra']))
                merged = apply_detail(dict(item), detail)
                db.update_detail_payload(control, merged)
                success += 1
            except Exception as exc:
                db.mark_detail_status(control, 'retry', str(exc)[:500])
                failed += 1
                errors.append(f'{control}: {exc}')
        status = 'success' if failed == 0 else ('partial' if success > 0 else 'error')
        db.finish_sync_run(run_id, status, 0, success, processed, '\n'.join(errors[:30]))
        return {'status': status, 'processed': processed, 'success': success, 'failed': failed, 'errors': errors}
    except Exception as exc:
        db.finish_sync_run(run_id, 'error', 0, success, processed, str(exc))
        raise



def run_cli() -> int:
    command = (sys.argv[1] if len(sys.argv) > 1 else 'quick').lower()
    if command == 'probe':
        print(probe_pncp_connection())
    elif command == 'quick':
        print(sync_quick())
    elif command == 'publicacao':
        print(sync_publications())
    elif command == 'proposta':
        print(sync_open_proposals())
    elif command == 'detalhe':
        print(enrich_pending_details())
    else:
        raise SystemExit(f'Comando inválido: {command}')
    return 0


if __name__ == '__main__':
    raise SystemExit(run_cli())
