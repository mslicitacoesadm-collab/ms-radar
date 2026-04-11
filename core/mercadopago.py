from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass
from typing import Dict
from urllib.parse import quote_plus

import requests

API_BASE = 'https://api.mercadopago.com'
TIMEOUT = 20


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    amount: float
    frequency: int
    frequency_type: str
    description: str


PLANS = {
    'mensal': Plan(
        code='mensal',
        name='MS Radar Pro Mensal',
        amount=49.90,
        frequency=1,
        frequency_type='months',
        description='Acesso recorrente mensal ao MS Radar com busca ampliada e leitura premium.',
    ),
    'anual': Plan(
        code='anual',
        name='MS Radar Pro Anual',
        amount=497.00,
        frequency=12,
        frequency_type='months',
        description='Acesso recorrente anual ao MS Radar com melhor custo e renovação automática.',
    ),
}


def _secret(name: str, default: str = '') -> str:
    try:
        import streamlit as st
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return os.getenv(name, default)


def access_token() -> str:
    return _secret('MP_ACCESS_TOKEN')


def public_app_url() -> str:
    return _secret('PUBLIC_APP_URL', 'http://localhost:8501').rstrip('/')


def configured() -> bool:
    return bool(access_token())


def headers() -> Dict[str, str]:
    token = access_token()
    if not token:
        raise RuntimeError('MP_ACCESS_TOKEN não configurado.')
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
        'X-Idempotency-Key': str(uuid.uuid4()),
    }


def create_preapproval(email: str, plan_code: str) -> Dict[str, object]:
    plan = PLANS[plan_code]
    external_reference = f'msradar-{plan.code}-{uuid.uuid4().hex[:18]}'
    back_url = f"{public_app_url()}?email={quote_plus(email)}&checkout=retorno&ext_ref={external_reference}"
    payload = {
        'reason': plan.name,
        'external_reference': external_reference,
        'payer_email': email,
        'back_url': back_url,
        'status': 'pending',
        'auto_recurring': {
            'frequency': plan.frequency,
            'frequency_type': plan.frequency_type,
            'transaction_amount': float(plan.amount),
            'currency_id': 'BRL',
        },
    }
    response = requests.post(f'{API_BASE}/preapproval', headers=headers(), data=json.dumps(payload), timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    data['external_reference'] = external_reference
    data['plan_code'] = plan.code
    data['amount'] = plan.amount
    data['frequency'] = plan.frequency
    data['frequency_type'] = plan.frequency_type
    return data


def get_preapproval(preapproval_id: str) -> Dict[str, object]:
    response = requests.get(f'{API_BASE}/preapproval/{preapproval_id}', headers=headers(), timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def cancel_preapproval(preapproval_id: str) -> Dict[str, object]:
    response = requests.put(
        f'{API_BASE}/preapproval/{preapproval_id}',
        headers=headers(),
        data=json.dumps({'status': 'cancelled'}),
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()
