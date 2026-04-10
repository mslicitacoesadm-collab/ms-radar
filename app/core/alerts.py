from __future__ import annotations

import smtplib
from email.message import EmailMessage

import requests

from .config import SETTINGS
from .database import log_delivery


def send_email_alert(to_email: str, subject: str, body: str) -> tuple[bool, str]:
    if not (SETTINGS.smtp_host and SETTINGS.smtp_user and SETTINGS.smtp_password and SETTINGS.smtp_from and to_email):
        return False, 'SMTP não configurado.'
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = SETTINGS.smtp_from
    msg['To'] = to_email
    msg.set_content(body)
    with smtplib.SMTP(SETTINGS.smtp_host, SETTINGS.smtp_port, timeout=20) as smtp:
        smtp.starttls()
        smtp.login(SETTINGS.smtp_user, SETTINGS.smtp_password)
        smtp.send_message(msg)
    return True, 'E-mail enviado.'


def send_telegram_alert(chat_id: str, body: str) -> tuple[bool, str]:
    token = SETTINGS.telegram_bot_token
    dest = chat_id or SETTINGS.telegram_chat_id
    if not (token and dest):
        return False, 'Telegram não configurado.'
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    response = requests.post(url, json={'chat_id': dest, 'text': body}, timeout=20)
    response.raise_for_status()
    return True, 'Mensagem enviada.'
