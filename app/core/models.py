from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Notice:
    source_id: str
    title: str
    object_text: str
    agency: str
    state: str
    city: str
    modality: str
    estimated_value: float
    publication_date: str
    deadline_date: str
    source_url: str
    source_system: str = "PNCP"
    raw_json: str = "{}"


@dataclass
class AlertProfile:
    id: Optional[int]
    name: str
    keywords: str
    state: str
    city: str
    modality: str
    min_value: float
    max_value: float
    email: str
    telegram_chat_id: str
    is_active: int = 1

