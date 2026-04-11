from __future__ import annotations

from typing import Dict, List

import streamlit as st

FREE_PREVIEW_LIMIT = 6


def ensure_state() -> None:
    if 'preview_limit' not in st.session_state:
        st.session_state.preview_limit = FREE_PREVIEW_LIMIT
    if 'premium_unlocked' not in st.session_state:
        st.session_state.premium_unlocked = False


def premium_active() -> bool:
    ensure_state()
    return bool(st.session_state.get('premium_unlocked'))


def unlock_premium() -> None:
    ensure_state()
    st.session_state.premium_unlocked = True


def reset_access() -> None:
    st.session_state.premium_unlocked = False
    st.session_state.preview_limit = FREE_PREVIEW_LIMIT


def obfuscate_items(items: List[Dict[str, object]]) -> List[Dict[str, object]]:
    ensure_state()
    if premium_active():
        return items
    result = []
    limit = int(st.session_state.preview_limit)
    for idx, item in enumerate(items):
        if idx < limit:
            result.append(item)
            continue
        hidden = dict(item)
        hidden['objeto'] = 'Oportunidade premium do MS Radar'
        hidden['orgao'] = 'Disponível na versão completa'
        hidden['municipio'] = 'Oculto'
        hidden['uf'] = '--'
        hidden['valor'] = 0
        hidden['valor_formatado'] = 'Desbloqueie para visualizar'
        hidden['modalidade'] = 'Conteúdo premium'
        hidden['nicho'] = 'Premium'
        hidden['fonte'] = ''
        hidden['encerramento'] = None
        hidden['urgencia'] = 'Prévia gratuita'
        result.append(hidden)
    return result
