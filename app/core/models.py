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
    source_system: str
    pncp_cnpj: str = ''
    pncp_ano: int = 0
    pncp_sequencial: int = 0
    opening_date: str = ''
    situation: str = ''
    score: float = 0.0
    urgency_score: float = 0.0
    fit_score: float = 0.0
    opportunity_score: float = 0.0
    match_reason: str = ''
    raw_json: Optional[str] = None
