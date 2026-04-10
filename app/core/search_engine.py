from __future__ import annotations

import math
import re
import unicodedata
from typing import Dict, Iterable, List

import pandas as pd


SEMANTIC_MAP = {
    "material de limpeza": ["limpeza", "higiene", "saneante", "descartavel", "descartáveis"],
    "merenda": ["alimenticio", "gêneros alimentícios", "generos alimenticios", "alimentação escolar", "merenda escolar"],
    "combustivel": ["gasolina", "diesel", "etanol", "lubrificante", "combustíveis"],
    "material grafico": ["gráfico", "impressão", "gráfica", "folder", "panfleto", "banner"],
    "medicamento": ["farmaceutico", "insumo hospitalar", "medicamentos", "material hospitalar"],
    "transporte escolar": ["ônibus", "micro-ônibus", "rota escolar", "locação de veículos"],
    "construcao": ["engenharia", "obra", "reforma", "manutenção predial", "serviço de engenharia"],
    "software": ["sistema", "licenciamento", "tecnologia", "suporte técnico", "plataforma"],
}


def normalize_text(text: str) -> str:
    text = text or ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text



def expand_query(query: str) -> List[str]:
    q = normalize_text(query)
    terms = [t for t in q.split() if len(t) > 1]
    expanded = list(terms)

    for base_term, synonyms in SEMANTIC_MAP.items():
        normalized_base = normalize_text(base_term)
        if normalized_base in q or any(term in normalized_base for term in terms):
            expanded.extend(normalize_text(s).split() for s in synonyms)

    flattened: List[str] = []
    for item in expanded:
        if isinstance(item, list):
            flattened.extend(item)
        else:
            flattened.append(item)

    return list(dict.fromkeys(flattened))



def compute_score(record: Dict, query: str) -> float:
    base = normalize_text(
        " ".join(
            [
                str(record.get("title", "")),
                str(record.get("object_text", "")),
                str(record.get("agency", "")),
                str(record.get("city", "")),
                str(record.get("state", "")),
                str(record.get("modality", "")),
            ]
        )
    )
    if not query.strip():
        freshness_bonus = 6.0 if record.get("deadline_date") else 2.0
        return freshness_bonus

    terms = expand_query(query)
    score = 0.0

    for term in terms:
        if term and term in base:
            score += 8.0

    whole_query = normalize_text(query)
    if whole_query and whole_query in base:
        score += 18.0

    title = normalize_text(str(record.get("title", "")))
    if whole_query and whole_query in title:
        score += 10.0

    value = float(record.get("estimated_value") or 0)
    if value >= 100000:
        score += min(10.0, math.log10(value + 1))

    if str(record.get("deadline_date", "")).strip():
        score += 4.0

    return round(score, 2)



def filter_and_rank(df: pd.DataFrame, query: str, state: str, city: str, modality: str, min_value: float, max_value: float) -> pd.DataFrame:
    if df.empty:
        return df

    work = df.copy()

    if state:
        work = work[work["state"].fillna("").str.upper() == state.upper()]
    if city:
        work = work[work["city"].fillna("").str.contains(city, case=False, na=False)]
    if modality:
        work = work[work["modality"].fillna("").str.contains(modality, case=False, na=False)]
    if min_value > 0:
        work = work[pd.to_numeric(work["estimated_value"], errors="coerce").fillna(0) >= min_value]
    if max_value > 0:
        work = work[pd.to_numeric(work["estimated_value"], errors="coerce").fillna(0) <= max_value]

    work["score"] = work.apply(lambda row: compute_score(row.to_dict(), query), axis=1)

    if query.strip():
        work = work[work["score"] > 0]

    work = work.sort_values(by=["score", "deadline_date", "publication_date"], ascending=[False, False, False])
    return work



def priority_label(score: float) -> str:
    if score >= 50:
        return "Alta"
    if score >= 25:
        return "Boa"
    if score >= 10:
        return "Moderada"
    return "Base"

