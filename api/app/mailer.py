"""Wysyłka e-maili przez SMTP (MailHog). Reply-To zawsze z requestu, nigdy od modelu."""

import logging
import smtplib
from email.message import EmailMessage

from app.config import Settings
from app.departments import Department

logger = logging.getLogger(__name__)

FROM_ADDRESS = "router@example.com"


def build_message(
    department: Department,
    reply_to: str,
    body: str,
    subject: str = "Nowe zgłoszenie od użytkownika",
) -> EmailMessage:
    msg = EmailMessage()
    msg["From"] = FROM_ADDRESS
    msg["To"] = department.email
    msg["Reply-To"] = reply_to
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def send_email(settings: Settings, department: Department, reply_to: str, body: str) -> None:
    msg = build_message(department=department, reply_to=reply_to, body=body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        smtp.send_message(msg)
    logger.info("mail wysłany: department=%s reply_to=%s", department.value, reply_to)
