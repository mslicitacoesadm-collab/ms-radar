from __future__ import annotations

"""Webhook opcional para atualização assíncrona de assinaturas.

Use este arquivo apenas se você quiser hospedar um endpoint separado.
O app Streamlit funciona sem webhook porque também valida a assinatura
quando o usuário retorna do checkout ou entra novamente com o e-mail.
"""

import json
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request

from core import mercadopago
from core.storage import update_subscription_status

app = FastAPI(title='MS Radar Mercado Pago Webhook')


@app.post('/webhooks/mercadopago')
async def mercado_pago_webhook(request: Request) -> Dict[str, Any]:
    payload = await request.json()
    data = payload.get('data') or {}
    preapproval_id = data.get('id') or data.get('preapproval_id')
    if not preapproval_id:
        return {'ok': True, 'ignored': True}
    try:
        remote = mercadopago.get_preapproval(str(preapproval_id))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    ext_ref = remote.get('external_reference')
    if not ext_ref:
        return {'ok': True, 'ignored': True}
    update_subscription_status(
        ext_ref,
        remote.get('status', 'pending'),
        preapproval_id=remote.get('id') or str(preapproval_id),
        raw_json=json.dumps(remote, ensure_ascii=False),
    )
    return {'ok': True, 'external_reference': ext_ref, 'status': remote.get('status')}
