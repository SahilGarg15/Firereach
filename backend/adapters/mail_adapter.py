"""
Mail Adapter — Gmail SMTP via aiosmtplib.
All email sending logic lives here. Swapping providers = one file change.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.message import EmailMessage
from uuid import uuid4

import aiosmtplib

from config import settings
from models import EmailAuthFailedError, EmailSendFailedError

logger = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


async def send(
    recipient: str,
    subject: str,
    body: str,
) -> dict[str, str]:
    """
    Send an email via Gmail SMTP.
    Returns { sent_at: str, message_id: str }.
    In MOCK_MODE, simulates sending without SMTP connection.
    """
    if settings.MOCK_MODE:
        message_id = f"<mock-{uuid4()}@firereach.local>"
        sent_at = datetime.now(timezone.utc).isoformat()
        logger.info("MOCK_MODE: simulated email send to %s", recipient)
        return {"sent_at": sent_at, "message_id": message_id}

    msg = EmailMessage()
    msg["From"] = settings.GMAIL_USER
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)

    message_id = f"<{uuid4()}@firereach.local>"
    msg["Message-ID"] = message_id

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=settings.GMAIL_USER,
            password=settings.GMAIL_APP_PASSWORD,
            timeout=30,
        )
    except aiosmtplib.SMTPAuthenticationError as exc:
        logger.error("SMTP auth failed: %s", exc)
        raise EmailAuthFailedError() from exc
    except (aiosmtplib.SMTPException, OSError) as exc:
        logger.error("SMTP send failed: %s", exc)
        raise EmailSendFailedError(email_body=body) from exc

    sent_at = datetime.now(timezone.utc).isoformat()
    logger.info("Email sent to %s, message_id=%s", recipient, message_id)
    return {"sent_at": sent_at, "message_id": message_id}
