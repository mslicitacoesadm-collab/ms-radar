from __future__ import annotations

from datetime import date, datetime, timedelta
import math
import re
import unicodedata


def only_digits(value: str | None) -> str:
    return ''.join(ch for ch in str(value or '') if ch.isdigit())


def normalize_text(value: str | None) -> str:
    text = str(value or '').strip()
    text = re.sub(r'\s+', ' ', text)
    return text


def slugify(value: str | None) -> str:
    text = unicodedata.normalize('NFKD', normalize_text(value)).encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^a-zA-Z0-9]+', '-', text).strip('-').lower()
    return text


def fold_text(value: str | None) -> str:
    text = unicodedata.normalize('NFKD', normalize_text(value)).encode('ascii', 'ignore').decode('ascii')
    return text.lower()


def compact_keywords(*values: str | None) -> str:
    parts = [fold_text(v) for v in values if normalize_text(v)]
    return ' '.join(parts)


def money(value: float | int | None) -> str:
    try:
        number = float(value or 0)
    except Exception:
        return 'R$ 0,00'
    formatted = f'{number:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return f'R$ {formatted}'


def parse_date(value: str | None) -> date | None:
    text = normalize_text(value)
    if not text:
        return None
    raw = text[:10]
    for fmt in ('%Y-%m-%d', '%Y%m%d'):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    return None


def pncp_date(value: date | datetime | str | None) -> str:
    if value is None:
        return ''
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime('%Y%m%d')
    dt = parse_date(value)
    return dt.strftime('%Y%m%d') if dt else ''


def iso_date(value: date | datetime | str | None) -> str:
    if value is None:
        return ''
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.isoformat()
    dt = parse_date(value)
    return dt.isoformat() if dt else normalize_text(str(value)[:10])


def daterange_days(days_back: int) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=max(0, days_back - 1))
    return pncp_date(start), pncp_date(end)


def human_days_to_deadline(value: str | None) -> int | None:
    dt = parse_date(value)
    if not dt:
        return None
    return (dt - date.today()).days


def summarize_object(objeto: str | None, limit: int = 115) -> str:
    text = normalize_text(objeto)
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0]
    return cut + '…'


def score_from_value(value: float | int | None) -> float:
    number = float(value or 0)
    if number <= 0:
        return 0.0
    # curva logarítmica simples
    return min(100.0, round(math.log10(max(number, 1)) * 20, 1))
