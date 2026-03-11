"""
FireReach API routes.
"""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from slowapi import Limiter
from slowapi.util import get_remote_address

from adapters import mail_adapter
from agent.orchestrator import run_agent
from models import (
    ConfirmSendRequest,
    ConfirmSendResponse,
    FireReachError,
    HealthResponse,
    RunRequest,
    RunResponse,
)
from config import settings

logger = logging.getLogger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# In-memory store for pending reviews (stateless per run lifecycle)
_pending_reviews: dict[str, dict] = {}


@router.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(mock_mode=settings.MOCK_MODE)


@router.post("/api/v1/run", response_model=RunResponse)
@limiter.limit("10/minute")
async def start_run(body: RunRequest, request: Request) -> RunResponse:
    """Start a new outreach run. Returns a run_id and stream URL."""
    run_id = str(uuid4())
    stream_url = f"/api/v1/run/{run_id}/stream"

    # Store run params for the stream endpoint
    _pending_reviews[f"params:{run_id}"] = {
        "company_name": body.company_name,
        "icp": body.icp,
        "recipient": body.recipient,
    }

    return RunResponse(run_id=run_id, stream_url=stream_url)


@router.get("/api/v1/run/{run_id}/stream")
async def stream_run(run_id: str) -> StreamingResponse:
    """
    SSE stream for a run. Executes the orchestrator as an async generator.
    Each event: "data: {json}\\n\\n"
    """
    params_key = f"params:{run_id}"
    params = _pending_reviews.pop(params_key, None)

    if not params:
        async def error_stream():
            yield 'event: error\ndata: {"step":0,"code":"VALIDATION_ERROR","message":"Invalid or expired run ID."}\n\n'
            yield f'event: done\ndata: {{"run_id":"{run_id}","total_duration_ms":0}}\n\n'

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    async def event_stream():
        async for event in run_agent(
            run_id=run_id,
            company_name=params["company_name"],
            icp=params["icp"],
            recipient=params["recipient"],
        ):
            yield event

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/v1/run/{run_id}/confirm-send", response_model=ConfirmSendResponse)
async def confirm_send(run_id: str, body: ConfirmSendRequest) -> ConfirmSendResponse:
    """
    Manually confirm and send an email that was held by the confidence gate.
    Only reachable when the confidence gate yielded review_required.
    """
    try:
        result = await mail_adapter.send(
            recipient=body.recipient,
            subject=body.email_subject,
            body=body.email_body,
        )
        return ConfirmSendResponse(
            sent_at=result["sent_at"],
            message_id=result["message_id"],
        )
    except FireReachError:
        raise
    except Exception as exc:
        logger.exception("Confirm send failed")
        raise FireReachError(
            code="EMAIL_SEND_FAILED",
            status_code=422,
            message="Email could not be sent. Copy the draft below.",
            payload={"email_body": body.email_body},
        ) from exc
