"""
FireReach Pydantic models — all request/response schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field, model_validator


# ── Signal Payload ──────────────────────────────────────────────────────────

class SignalPayload(BaseModel):
    """Buyer-intent signals harvested for a target company."""

    funding: Optional[str] = None
    leadership: Optional[str] = None
    hiring: Optional[str] = None
    social_mentions: Optional[str] = None
    tech_stack: Optional[str] = None
    keyword_intent: Optional[str] = None
    news: Optional[str] = None

    # Always None — requires paid provider (e.g. G2 Buyer Intent API, 6sense, Bombora)
    website_visits: None = None       # Requires paid provider — e.g. 6sense, Bombora
    g2_surges: None = None            # Requires paid provider — e.g. G2 Buyer Intent API
    competitor_churn: None = None     # Requires paid provider — e.g. G2, Klue
    product_usage: None = None        # Requires paid provider — e.g. Pendo, Amplitude

    source_urls: list[str] = Field(default_factory=list)
    signal_count: int = 0

    @model_validator(mode="before")
    @classmethod
    def compute_signal_count(cls, values: dict) -> dict:
        """Count non-None fetchable signal fields."""
        fetchable = [
            "funding", "leadership", "hiring", "social_mentions",
            "tech_stack", "keyword_intent", "news",
        ]
        count = sum(1 for f in fetchable if values.get(f) is not None)
        values["signal_count"] = count
        return values


# ── Request / Response Models ───────────────────────────────────────────────

class RunRequest(BaseModel):
    """POST /api/v1/run request body."""
    icp: str = Field(..., min_length=10, max_length=500, description="Ideal Customer Profile description")
    company_name: str = Field(..., min_length=2, max_length=100, description="Target company name")
    recipient: EmailStr = Field(..., description="Recipient email address")


class RunResponse(BaseModel):
    """POST /api/v1/run response body."""
    run_id: UUID = Field(default_factory=uuid4)
    stream_url: str


class HealthResponse(BaseModel):
    """GET /api/health response body."""
    status: str = "ok"
    version: str = "1.0.0"
    mock_mode: bool


# ── SSE Event Models ────────────────────────────────────────────────────────

class StepUpdate(BaseModel):
    """SSE event: step_update."""
    step: int
    status: str
    label: str


class StepComplete(BaseModel):
    """SSE event: step_complete."""
    step: int
    status: str
    payload: dict


class ErrorEvent(BaseModel):
    """SSE event: error."""
    step: int
    code: str
    message: str


class ReviewRequired(BaseModel):
    """SSE event: review_required (confidence gate)."""
    type: str = "review_required"
    subject: str
    body: str
    score: int
    run_id: str


class DoneEvent(BaseModel):
    """SSE event: done."""
    run_id: str
    total_duration_ms: int


# ── Confirm Send ────────────────────────────────────────────────────────────

class ConfirmSendRequest(BaseModel):
    """POST /api/v1/run/{run_id}/confirm-send request body."""
    email_subject: str
    email_body: str
    recipient: EmailStr


class ConfirmSendResponse(BaseModel):
    """POST /api/v1/run/{run_id}/confirm-send response body."""
    sent_at: str
    message_id: str


# ── Typed Errors ────────────────────────────────────────────────────────────

class FireReachError(Exception):
    """Base error with typed code and user-facing message."""

    def __init__(self, code: str, status_code: int, message: str, payload: Optional[dict] = None):
        self.code = code
        self.status_code = status_code
        self.message = message
        self.payload = payload or {}
        super().__init__(message)


class SignalNotFoundError(FireReachError):
    def __init__(self) -> None:
        super().__init__(
            code="SIGNAL_NOT_FOUND",
            status_code=422,
            message="No signals found for this company. Check the name and retry.",
        )


class SignalApiLimitError(FireReachError):
    def __init__(self) -> None:
        super().__init__(
            code="SIGNAL_API_LIMIT",
            status_code=503,
            message="Signal service temporarily unavailable. Try again shortly.",
        )


class SignalApiError(FireReachError):
    def __init__(self) -> None:
        super().__init__(
            code="SIGNAL_API_ERROR",
            status_code=502,
            message="Signal fetch failed. Try again.",
        )


class LlmTimeoutError(FireReachError):
    def __init__(self) -> None:
        super().__init__(
            code="LLM_TIMEOUT",
            status_code=504,
            message="AI model timed out. Please retry.",
        )


class LlmApiError(FireReachError):
    def __init__(self) -> None:
        super().__init__(
            code="LLM_API_ERROR",
            status_code=502,
            message="AI service error. Try again.",
        )


class EmailAuthFailedError(FireReachError):
    def __init__(self) -> None:
        super().__init__(
            code="EMAIL_AUTH_FAILED",
            status_code=500,
            message="Email auth failed. Check server credentials.",
        )


class EmailSendFailedError(FireReachError):
    def __init__(self, email_body: str = "") -> None:
        super().__init__(
            code="EMAIL_SEND_FAILED",
            status_code=422,
            message="Email could not be sent. Copy the draft below.",
            payload={"email_body": email_body},
        )


class TemplateViolationError(FireReachError):
    def __init__(self) -> None:
        super().__init__(
            code="TEMPLATE_VIOLATION",
            status_code=500,
            message="Email quality check failed after retry. Signals may be insufficient for this company.",
        )
