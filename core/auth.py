from __future__ import annotations

import re
from typing import Optional

import streamlit as st

from .storage import upsert_user

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def normalize_email(value: str) -> str:
    return (value or '').strip().lower()


def valid_email(value: str) -> bool:
    return bool(EMAIL_RE.match(normalize_email(value)))


def ensure_user(email: str) -> str:
    email = normalize_email(email)
    if not valid_email(email):
        raise ValueError('Informe um e-mail válido para continuar.')
    upsert_user(email)
    st.session_state['user_email'] = email
    return email


def get_user_email() -> Optional[str]:
    email = st.session_state.get('user_email') or st.query_params.get('email')
    if email:
        email = normalize_email(str(email))
        if valid_email(email):
            st.session_state['user_email'] = email
            return email
    return None
