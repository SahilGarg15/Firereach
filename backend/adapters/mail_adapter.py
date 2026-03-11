"""
Mail Adapter — Resend API for transactional email.
All email sending logic lives here. Swapping providers = one file change.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import uuid4

import httpx

from config import settings
from models import EmailAuthFailedError, EmailSendFailedError

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


async def send(
    recipient: str,
    subject: str,
    body: str,
) -> dict[str, str]:
    """
    Send an email via Resend API.
    Returns { sent_at: str, message_id: str }.
    In MOCK_MODE, simulates sending without any external call.
    """
    if settings.MOCK_MODE:
        message_id = f"<mock-{uuid4()}@firereach.local>"
        sent_at = datetime.now(timezone.utc).isoformat()
        logger.info("MOCK_MODE: simulated email send to %s", recipient)
        return {"sent_at": sent_at, "message_id": message_id}

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": settings.RESEND_FROM,
                    "to": [recipient],
                    "subject": subject,
                    "text": body,
                },
                timeout=30,
            )

        if resp.status_code == 403:
            logger.error("Resend auth failed: %s", resp.text)
            raise EmailAuthFailedError()
        if resp.status_code != 200:
            logger.error("Resend send failed (%d): %s", resp.status_code, resp.text)
            raise EmailSendFailedError(email_body=body)

        data = resp.json()
        message_id = data.get("id", f"<{uuid4()}@resend>")

    except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
        logger.error("Resend API error: %s", exc)
        raise EmailSendFailedError(email_body=body) from exc

    sent_at = datetime.now(timezone.utc).isoformat()
    logger.info("Email sent to %s via Resend, id=%s", recipient, message_id)
    return {"sent_at": sent_at, "message_id": message_id}
