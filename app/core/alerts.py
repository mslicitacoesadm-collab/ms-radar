from __future__ import annotations

import smtplib
from email.mime.text import MIMEText
from typing import Dict, Iterable, List

import requests

from .config import load_settings
from .database import delivery_exists, register_delivery
from .search_engine import compute_score, normalize_text


settings = load_settings()


def match_alert(alert: Dict, notice: Dict) -> bool:
    if not int(alert.get("is_active", 1)):
        return False

    if alert.get("state") and (notice.get("state") or "").upper() != str(alert.get("state")).upper():
        return False
    if alert.get("city") and normalize_text(str(alert.get("city"))) not in normalize_text(str(notice.get("city", ""))):
        return False
    if alert.get("modality") and normalize_text(str(alert.get("modality"))) not in normalize_text(str(notice.get("modality", ""))):
        return False

    value = float(notice.get("estimated_value") or 0)
    min_value = float(alert.get("min_value") or 0)
    max_value = float(alert.get("max_value") or 0)
    if min_value > 0 and value < min_value:
        return False
    if max_value > 0 and value > max_value:
        return False

    query = str(alert.get("keywords") or "").strip()
    if query:
        return compute_score(notice, query) > 0

    return True



def build_message(alert: Dict, notice: Dict) -> str:
    return (
        f"Novo aviso para o alerta '{alert.get('name')}'\n\n"
        f"Título: {notice.get('title')}\n"
        f"Órgão: {notice.get('agency')}\n"
        f"Cidade/UF: {notice.get('city')}/{notice.get('state')}\n"
        f"Modalidade: {notice.get('modality')}\n"
        f"Valor estimado: R$ {float(notice.get('estimated_value') or 0):,.2f}\n"
        f"Publicação: {notice.get('publication_date')}\n"
        f"Prazo: {notice.get('deadline_date')}\n"
        f"Link: {notice.get('source_url')}\n"
    )



def send_email(subject: str, body: str, to_address: str) -> bool:
    if not (settings.smtp_host and settings.smtp_user and settings.smtp_password and settings.smtp_from and to_address):
        return False

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to_address

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)
    return True



def send_telegram(body: str, chat_id: str) -> bool:
    token = settings.telegram_bot_token
    chat = chat_id or settings.telegram_chat_id
    if not token or not chat:
        return False

    response = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": body},
        timeout=20,
    )
    response.raise_for_status()
    return True



def process_alerts(alerts: Iterable[Dict], notices: Iterable[Dict]) -> List[Dict]:
    deliveries: List[Dict] = []
    for alert in alerts:
        for notice in notices:
            if not match_alert(alert, notice):
                continue

            body = build_message(alert, notice)
            subject = f"Radar de Licitações | {notice.get('city')}/{notice.get('state')} | {notice.get('title')}"

            if alert.get("email") and not delivery_exists(int(alert["id"]), str(notice["source_id"]), "email"):
                if send_email(subject, body, str(alert["email"])):
                    register_delivery(int(alert["id"]), str(notice["source_id"]), "email")
                    deliveries.append({"alert_id": alert["id"], "source_id": notice["source_id"], "channel": "email"})

            chat_id = str(alert.get("telegram_chat_id") or "")
            if chat_id and not delivery_exists(int(alert["id"]), str(notice["source_id"]), "telegram"):
                if send_telegram(body, chat_id):
                    register_delivery(int(alert["id"]), str(notice["source_id"]), "telegram")
                    deliveries.append({"alert_id": alert["id"], "source_id": notice["source_id"], "channel": "telegram"})

    return deliveries

