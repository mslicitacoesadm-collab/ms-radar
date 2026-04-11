from __future__ import annotations

import json
from typing import Dict, List, Optional, Tuple

from . import mercadopago
from .storage import get_latest_active_subscription, list_subscriptions_by_email, save_subscription, update_subscription_status

FREE_PREVIEW_LIMIT = 6


def register_checkout(email: str, plan_code: str) -> Dict[str, object]:
    response = mercadopago.create_preapproval(email, plan_code)
    save_subscription({
        'email': email,
        'external_reference': response.get('external_reference'),
        'preapproval_id': response.get('id'),
        'plan_code': response.get('plan_code'),
        'amount': response.get('amount'),
        'frequency': response.get('frequency'),
        'frequency_type': response.get('frequency_type'),
        'checkout_url': response.get('init_point') or response.get('sandbox_init_point'),
        'status': response.get('status', 'pending'),
        'payer_email': email,
        'raw_json': json.dumps(response, ensure_ascii=False),
    })
    return response


def sync_email_subscription(email: str) -> Tuple[Optional[Dict[str, object]], List[Dict[str, object]], Optional[str]]:
    subs = list_subscriptions_by_email(email)
    last_error = None
    for item in subs:
        preapproval_id = item.get('preapproval_id')
        if not preapproval_id or not mercadopago.configured():
            continue
        try:
            remote = mercadopago.get_preapproval(preapproval_id)
            update_subscription_status(
                item['external_reference'],
                remote.get('status', item.get('status') or 'pending'),
                preapproval_id=remote.get('id') or preapproval_id,
                raw_json=json.dumps(remote, ensure_ascii=False),
            )
        except Exception as exc:
            last_error = str(exc)
    subs = list_subscriptions_by_email(email)
    active = get_latest_active_subscription(email)
    return active, subs, last_error


def obfuscate_items(items: List[Dict[str, object]], premium: bool) -> List[Dict[str, object]]:
    if premium:
        return items
    result = []
    for idx, item in enumerate(items):
        if idx < FREE_PREVIEW_LIMIT:
            result.append(item)
            continue
        hidden = dict(item)
        hidden['objeto'] = 'Oportunidade premium do MS Radar'
        hidden['orgao'] = 'Disponível para assinantes'
        hidden['municipio'] = 'Oculto'
        hidden['uf'] = '--'
        hidden['valor'] = 0
        hidden['valor_formatado'] = 'Desbloqueie para visualizar'
        hidden['modalidade'] = 'Conteúdo premium'
        hidden['nicho'] = 'Premium'
        hidden['fonte'] = ''
        result.append(hidden)
    return result
