from __future__ import annotations

from datetime import datetime
import re
from typing import Iterable


def to_iso_date(value: str | datetime | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.strftime('%Y-%m-%d')
    text = str(value).strip()
    if not text:
        return None
    return text[:10]


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace('Z', '+00:00')
    try:
        return datetime.fromisoformat(text)
    except Exception:
        return None


def clean_text(value: str | None) -> str:
    if not value:
        return ''
    text = re.sub(r'\s+', ' ', str(value)).strip()
    return text


def compact_keywords(*parts: str | None) -> str:
    bag: list[str] = []
    for part in parts:
        text = clean_text(part)
        if text:
            bag.append(text)
    return ' | '.join(bag)


def bool_icon(flag: bool) -> str:
    return 'Sim' if flag else 'Não'


def money(value: float | int | None) -> str:
    if value is None:
        return '—'
    return f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def unique_words(texts: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    words: list[str] = []
    for text in texts:
        for word in re.findall(r'[\wÀ-ÿ-]{3,}', text.lower()):
            if word not in seen:
                seen.add(word)
                words.append(word)
    return words
