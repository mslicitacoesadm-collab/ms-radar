from __future__ import annotations

from app.core.database import Database


def evaluate_alerts(limit_per_alert: int = 10) -> dict:
    db = Database()
    report = {'alerts': []}
    for alert in db.list_alert_profiles():
        rows = db.search_opportunities(
            query=alert['termos'],
            uf=alert['uf_sigla'] or '',
            municipio=alert['municipio_nome'] or '',
            modalidade_codigo=alert['modalidade_codigo'],
            only_open=bool(alert['somente_abertas']),
            valor_min=alert['valor_min'],
            valor_max=alert['valor_max'],
            limit=limit_per_alert,
        )
        report['alerts'].append({'alerta': dict(alert), 'total_matches': len(rows), 'matches': [dict(r) for r in rows]})
    return report
