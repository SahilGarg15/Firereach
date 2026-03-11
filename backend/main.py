"""
FireReach — FastAPI application entry point.
CORS, rate limiter, startup checks, error handlers.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from config import settings
from models import FireReachError
from routers.run import limiter, router

# ── Logging ─────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="FireReach",
    description="Autonomous B2B outreach engine by Rabbitt AI",
    version="1.0.0",
)

# ── CORS ────────────────────────────────────────────────────────────────────

origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Rate Limiter ────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Routes ──────────────────────────────────────────────────────────────────

app.include_router(router)

# ── Error Handlers ──────────────────────────────────────────────────────────

@app.exception_handler(FireReachError)
async def firereach_error_handler(request: Request, exc: FireReachError) -> JSONResponse:
    """Return typed JSON errors. No raw stack traces reach the client."""
    payload = {"code": exc.code, "message": exc.message}
    if exc.payload:
        payload["payload"] = exc.payload
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: no raw stack traces reach the client."""
    logger.exception("Unhandled error")
    return JSONResponse(
        status_code=500,
        content={"code": "LLM_API_ERROR", "message": "AI service error. Try again."},
    )


# ── Startup ─────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_checks() -> None:
    """Validate configuration on startup. Fail loudly if env vars missing."""
    logger.info("FireReach starting up...")
    logger.info("MOCK_MODE: %s", settings.MOCK_MODE)
    logger.info("ALLOWED_ORIGINS: %s", settings.ALLOWED_ORIGINS)
    logger.info("LOG_LEVEL: %s", settings.LOG_LEVEL)

    if settings.MOCK_MODE:
        logger.warning("Running in MOCK_MODE — no external API calls will be made.")
    else:
        # Verify required keys are not placeholder values
        if settings.GROQ_API_KEY.startswith("your_"):
            logger.error("GROQ_API_KEY appears to be a placeholder. Set a real key or enable MOCK_MODE.")
        if settings.SERP_API_KEY.startswith("your_"):
            logger.error("SERP_API_KEY appears to be a placeholder. Set a real key or enable MOCK_MODE.")

    logger.info("FireReach ready.")
