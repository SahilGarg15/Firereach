"""
Mail Adapter — SendGrid API for transactional email.
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

SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"


async def send(
    recipient: str,
    subject: str,
    body: str,
) -> dict[str, str]:
    """
    Send an email via SendGrid API.
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
                SENDGRID_API_URL,
                headers={
                    "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": recipient}]}],
                    "from": {"email": settings.SENDGRID_FROM, "name": "FireReach"},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": body}],
                },
                timeout=30,
            )

        if resp.status_code in (401, 403):
            logger.error("SendGrid auth failed: %s", resp.text)
            raise EmailAuthFailedError()
        if resp.status_code not in (200, 202):
            logger.error("SendGrid send failed (%d): %s", resp.status_code, resp.text)
            raise EmailSendFailedError(email_body=body)

        # SendGrid returns 202 with no body on success; use X-Message-Id header
        message_id = resp.headers.get("X-Message-Id", f"{uuid4()}")

    except (httpx.TimeoutException, httpx.ConnectError, OSError) as exc:
        logger.error("SendGrid API error: %s", exc)
        raise EmailSendFailedError(email_body=body) from exc

    sent_at = datetime.now(timezone.utc).isoformat()
    logger.info("Email sent to %s via SendGrid, id=%s", recipient, message_id)
    return {"sent_at": sent_at, "message_id": message_id}
