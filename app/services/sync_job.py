from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from app.core.config import DEFAULT_MODALIDADES_SCAN, SyncWindow
from app.core.database import Database
from app.core.pncp_client import PNCPClient, PNCPClientError, PNCPValidationError
from app.core.search_engine import apply_detail, normalize_summary_item


def probe_pncp_connection(codigo_modalidade: int | None = None) -> dict[str, Any]:
    client = PNCPClient()
    result = client.probe(codigo_modalidade=codigo_modalidade)
    return {
        'ok': result.ok,
        'status_code': result.status_code,
        'elapsed_seconds': result.elapsed_seconds,
        'message': result.message,
    }


def _iter_modalidades(codigo_modalidade: int | None) -> Iterable[int | None]:
    if codigo_modalidade is not None:
        yield codigo_modalidade
    else:
        yield None


def sync_open_summaries(
    *,
    codigo_modalidade: int | None = None,
    max_pages: int = SyncWindow.max_pages,
    page_size: int = SyncWindow.page_size,
) -> dict[str, Any]:
    db = Database()
    client = PNCPClient()
    data_final = date.today().isoformat()
    run_id = db.create_sync_run('PNCP_SUMMARY', details=f'data_final={data_final};modalidade={codigo_modalidade};max_pages={max_pages};page_size={page_size}')
    imported = updated = seen = 0
    page_errors: list[str] = []
    rows: list[dict[str, Any]] = []
    modalidades_usadas: list[int | None] = []
    try:
        modalidades_tentativa = list(_iter_modalidades(codigo_modalidade))
        auto_scan = False
        for modalidade in modalidades_tentativa:
            try:
                for pagina in range(1, max_pages + 1):
                    payload = client.list_open_opportunities(
                        data_final=data_final,
                        pagina=pagina,
                        tamanho_pagina=page_size,
                        codigo_modalidade=modalidade,
                    )
                    modalidades_usadas.append(modalidade)
                    items = payload.get('data', []) if isinstance(payload, dict) else []
                    if not items:
                        break
                    for item in items:
                        seen += 1
                        row = normalize_summary_item(item, 'proposta_aberta', data_final)
                        if row['numero_controle_pncp']:
                            rows.append(row)
                    total_paginas = int(payload.get('totalPaginas') or 0)
                    if total_paginas and pagina >= total_paginas:
                        break
            except PNCPValidationError:
                if codigo_modalidade is None and not auto_scan:
                    auto_scan = True
                    modalidades_tentativa = DEFAULT_MODALIDADES_SCAN
                    modalidades_usadas = []
                    rows = []
                    seen = 0
                    break
                raise
            except PNCPClientError as exc:
                page_errors.append(f'modalidade={modalidade} erro={exc}')
                continue
        if auto_scan:
            for modalidade in DEFAULT_MODALIDADES_SCAN:
                for pagina in range(1, max_pages + 1):
                    try:
                        payload = client.list_open_opportunities(
                            data_final=data_final,
                            pagina=pagina,
                            tamanho_pagina=page_size,
                            codigo_modalidade=modalidade,
                        )
                        modalidades_usadas.append(modalidade)
                    except PNCPClientError as exc:
                        page_errors.append(f'modalidade={modalidade};pagina={pagina};erro={exc}')
                        break
                    items = payload.get('data', []) if isinstance(payload, dict) else []
                    if not items:
                        break
                    for item in items:
                        seen += 1
                        row = normalize_summary_item(item, 'proposta_aberta', data_final)
                        if row['numero_controle_pncp']:
                            rows.append(row)
                    total_paginas = int(payload.get('totalPaginas') or 0)
                    if total_paginas and pagina >= total_paginas:
                        break
        imported, updated = db.upsert_opportunities(rows, detail_status='summary')
        details = f'rows={len(rows)};modalidades={sorted({m for m in modalidades_usadas if m is not None})};erros={len(page_errors)}'
        if page_errors:
            details += '\n' + '\n'.join(page_errors[:20])
        db.finish_sync_run(run_id, 'success' if rows or not page_errors else 'partial', imported, updated, seen, details=details)
        return {
            'status': 'success' if rows or not page_errors else 'partial',
            'imported': imported,
            'updated': updated,
            'seen': seen,
            'rows': len(rows),
            'errors': page_errors,
        }
    except PNCPClientError as exc:
        db.finish_sync_run(run_id, 'error', imported, updated, seen, details=str(exc))
        raise


def enrich_pending_details(batch_size: int = SyncWindow.detail_batch_size) -> dict[str, Any]:
    db = Database()
    client = PNCPClient()
    run_id = db.create_sync_run('PNCP_DETAIL', details=f'batch_size={batch_size}')
    processed = success = failed = 0
    errors: list[str] = []
    try:
        rows = db.pending_detail_candidates(limit=batch_size)
        for item in rows:
            processed += 1
            control = item['numero_controle_pncp']
            try:
                detail = client.get_opportunity_detail(
                    cnpj=item['orgao_cnpj'],
                    ano=int(item['ano_compra']),
                    sequencial=int(item['sequencial_compra']),
                )
                merged = apply_detail(dict(item), detail)
                db.update_detail_payload(control, merged)
                success += 1
            except PNCPClientError as exc:
                db.mark_detail_status(control, 'retry', str(exc)[:500])
                failed += 1
                errors.append(f'{control}: {exc}')
            except Exception as exc:
                db.mark_detail_status(control, 'retry', str(exc)[:500])
                failed += 1
                errors.append(f'{control}: {exc}')
        db.finish_sync_run(run_id, 'success' if failed == 0 else 'partial', 0, success, processed, details='\n'.join(errors[:20]))
        return {'status': 'success' if failed == 0 else 'partial', 'processed': processed, 'success': success, 'failed': failed, 'errors': errors}
    except PNCPClientError as exc:
        db.finish_sync_run(run_id, 'error', 0, success, processed, details=str(exc))
        raise


if __name__ == '__main__':
    print(sync_open_summaries())
