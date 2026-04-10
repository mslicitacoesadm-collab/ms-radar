from __future__ import annotations

import math
from datetime import datetime
from typing import Iterable

import pandas as pd

SYNONYMS = {
    'material grafico': ['grafico', 'impressos', 'papelaria'],
    'combustivel': ['gasolina', 'diesel', 'lubrificante'],
    'merenda': ['alimenticios', 'gêneros', 'escolar'],
    'limpeza': ['higiene', 'saneantes', 'descartáveis'],
    'engenharia': ['obra', 'reforma', 'construção'],
    'software': ['sistema', 'licenciamento', 'implantação'],
}


def _tokenize(text: str) -> list[str]:
    cleaned = ''.join(ch.lower() if ch.isalnum() or ch.isspace() else ' ' for ch in (text or ''))
    return [t for t in cleaned.split() if len(t) > 1]


def _expanded_terms(query: str) -> set[str]:
    terms = set(_tokenize(query))
    normalized = ' '.join(sorted(terms))
    for key, values in SYNONYMS.items():
        if any(k in query.lower() for k in key.split()):
            terms.update(values)
    if 'ti' in terms:
        terms.update(['software', 'sistema', 'tecnologia'])
    return terms


def score_row(row: pd.Series, query: str, profile_terms: set[str] | None = None) -> dict[str, float | str]:
    text = ' '.join([
        str(row.get('title', '')),
        str(row.get('object_text', '')),
        str(row.get('agency', '')),
        str(row.get('city', '')),
        str(row.get('modality', '')),
    ]).lower()
    tokens = set(_tokenize(text))
    q_terms = _expanded_terms(query)
    if profile_terms:
        q_terms |= profile_terms

    matches = len(tokens & q_terms)
    base_score = matches / max(len(q_terms), 1)

    estimated = float(row.get('estimated_value', 0) or 0)
    value_score = min(math.log10(estimated + 1) / 7, 1.0)

    deadline_score = 0.3
    deadline = str(row.get('deadline_date', '') or '')
    if deadline:
        try:
            days = (datetime.fromisoformat(deadline) - datetime.now()).days
            if days <= 2:
                deadline_score = 1.0
            elif days <= 7:
                deadline_score = 0.8
            elif days <= 15:
                deadline_score = 0.6
            else:
                deadline_score = 0.35
        except ValueError:
            pass

    fit_score = min(1.0, base_score * 1.3)
    opportunity = round((fit_score * 0.5 + value_score * 0.3 + deadline_score * 0.2) * 100, 1)

    if matches >= 3:
        reason = 'Alta aderência ao objeto pesquisado'
    elif matches == 2:
        reason = 'Boa aderência semântica'
    elif matches == 1:
        reason = 'Correspondência parcial relevante'
    else:
        reason = 'Encontrado por filtros estruturados'

    return {
        'score': round(base_score * 100, 1),
        'fit_score': round(fit_score * 100, 1),
        'urgency_score': round(deadline_score * 100, 1),
        'opportunity_score': opportunity,
        'match_reason': reason,
    }


def apply_scoring(df: pd.DataFrame, query: str, profile_terms: set[str] | None = None) -> pd.DataFrame:
    if df.empty:
        return df
    scored = [score_row(row, query, profile_terms) for _, row in df.iterrows()]
    score_df = pd.DataFrame(scored)
    out = pd.concat([df.reset_index(drop=True), score_df], axis=1)
    return out.sort_values(['opportunity_score', 'fit_score', 'estimated_value'], ascending=[False, False, False])
