from __future__ import annotations

from typing import Any

from app.core.database import Database


def evaluate_alerts(limit_per_alert: int = 30) -> dict[str, Any]:
    db = Database()
    alerts = db.list_alert_profiles()
    report: list[dict[str, Any]] = []
    with db.connect() as conn:
        for alert in alerts:
            terms = [term.strip() for term in (alert['termos'] or '').split(',') if term.strip()]
            where = []
            params: list[Any] = []
            if terms:
                sub = []
                for term in terms:
                    sub.append('search_blob LIKE ?')
                    params.append(f'%{term}%')
                where.append('(' + ' OR '.join(sub) + ')')
            if alert['uf_sigla']:
                where.append('uf_sigla = ?')
                params.append(alert['uf_sigla'])
            if alert['municipio_nome']:
                where.append('municipio_nome = ?')
                params.append(alert['municipio_nome'])
            if alert['modalidade_codigo']:
                where.append('modalidade_codigo = ?')
                params.append(alert['modalidade_codigo'])
            if alert['valor_min'] is not None:
                where.append('valor_total_estimado >= ?')
                params.append(alert['valor_min'])
            if alert['valor_max'] is not None:
                where.append('valor_total_estimado <= ?')
                params.append(alert['valor_max'])
            if alert['somente_abertas']:
                where.append("date(data_encerramento_proposta) >= date('now')")
            sql = 'SELECT * FROM opportunities'
            if where:
                sql += ' WHERE ' + ' AND '.join(where)
            sql += ' ORDER BY oportunidade_score DESC, data_encerramento_proposta ASC LIMIT ?'
            params.append(limit_per_alert)
            rows = conn.execute(sql, params).fetchall()
            report.append({'alerta': dict(alert), 'matches': [dict(r) for r in rows], 'total_matches': len(rows)})
    return {'alerts': report}
