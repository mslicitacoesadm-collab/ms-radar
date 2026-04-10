from __future__ import annotations

import argparse

from app.core.database import insert_sync_history, upsert_notices
from app.core.pncp_client import fetch_open_notices, load_demo_notices


def main() -> None:
    parser = argparse.ArgumentParser(description='Sincroniza oportunidades do PNCP para a base local.')
    parser.add_argument('--days', type=int, default=30)
    parser.add_argument('--uf', type=str, default='')
    parser.add_argument('--demo-fallback', action='store_true')
    args = parser.parse_args()

    try:
        notices = fetch_open_notices(days_ahead=args.days, uf=args.uf)
        imported = upsert_notices(notices)
        insert_sync_history('pncp', imported, 'ok', f'UF={args.uf or "TODAS"}')
        print(f'Importadas {imported} oportunidades do PNCP.')
    except Exception as exc:
        if args.demo_fallback:
            notices = load_demo_notices()
            imported = upsert_notices(notices)
            insert_sync_history('demo', imported, 'fallback', str(exc))
            print(f'Falha no PNCP. Base demo carregada com {imported} registros. Motivo: {exc}')
        else:
            insert_sync_history('pncp', 0, 'erro', str(exc))
            raise


if __name__ == '__main__':
    main()
