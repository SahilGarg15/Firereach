"""
FireReach configuration — Pydantic BaseSettings.
Reads from .env. Fails loudly on startup if any required variable is missing.
"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Required — startup fails if missing
    GROQ_API_KEY: str = Field(..., description="Groq API key for LLM calls")
    SERP_API_KEY: str = Field(..., description="SerpAPI key for signal harvesting")
    GMAIL_USER: str = Field(..., description="Gmail address for sending outreach")
    GMAIL_APP_PASSWORD: str = Field(..., description="Gmail 16-char app password")

    # Optional — sensible defaults
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:5173",
        description="Comma-separated CORS origins",
    )
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    MOCK_MODE: bool = Field(
        default=False,
        description="When true, adapters return fixtures and make zero external API calls",
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
