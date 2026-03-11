"""
LLM Adapter — Groq SDK wrapper with retry and typed error mapping.
All Groq interactions go through this module. Swapping providers = one file change.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from groq import AsyncGroq, APITimeoutError, APIStatusError

from config import settings
from models import LlmTimeoutError, LlmApiError

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"
MAX_RETRIES = 2
RETRY_DELAY = 1.0  # seconds

# ── Mock fixture ────────────────────────────────────────────────────────────

MOCK_BRIEF = (
    "Acme Corp is experiencing rapid growth following their $18M Series B led by Sequoia. "
    "They are actively hiring 12 engineering roles focused on platform security, and have been "
    "featured in TechCrunch's 'Startups to Watch' list with over 3.1K social mentions this week. "
    "Their tech stack references AWS, Kubernetes, and SOC2 compliance preparation, indicating "
    "a serious commitment to security infrastructure.\n\n"
    "This growth trajectory makes Acme Corp an ideal target for high-end cybersecurity training. "
    "With 12 new engineering hires onboarding into a platform security focus, their team will need "
    "hands-on security training immediately. The SOC2 compliance prep signals a compliance deadline "
    "that creates urgency. Their Series B funding means budget is available, and the EMEA expansion "
    "increases their attack surface — making security training not just valuable but essential."
)

MOCK_EMAIL_SUBJECT = "Acme Corp's security expansion — training for your 12 new engineers"
MOCK_EMAIL_BODY = (
    "Hi there,\n\n"
    "I noticed Acme Corp raised $18M in a Series B round led by Sequoia and is actively "
    "hiring 12 engineering roles focused on platform security. With Sarah Chen joining as CTO "
    "from Stripe, your leadership team clearly has enterprise security in its DNA.\n\n"
    "Your tech stack references Kubernetes and active SOC2 compliance prep, and with your "
    "announced EMEA expansion and new enterprise tier, your attack surface is growing fast. "
    "Featured in TechCrunch as a startup to watch with thousands of social mentions this week, "
    "the momentum is clear.\n\n"
    "We specialize in high-end cybersecurity training for fast-growing startups at exactly this "
    "inflection point. Our programs get new engineering hires security-ready within 30 days — "
    "critical when you're onboarding 12 platform security engineers during a compliance push.\n\n"
    "Would a 15-minute call this week make sense to explore how we can support your team's "
    "security readiness?\n\n"
    "Best regards"
)


def _build_client() -> AsyncGroq:
    """Create an AsyncGroq client."""
    return AsyncGroq(api_key=settings.GROQ_API_KEY)


async def chat_completion(
    messages: list[dict[str, str]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str | None = None,
    mock_tool_name: str | None = None,
) -> dict[str, Any]:
    """
    Send a chat completion request to Groq with retry logic.

    Returns the full response message dict including any tool_calls.
    In MOCK_MODE, returns mock responses based on mock_tool_name.
    """
    if settings.MOCK_MODE:
        return _mock_response(mock_tool_name)

    client = _build_client()

    for attempt in range(MAX_RETRIES + 1):
        try:
            kwargs: dict[str, Any] = {
                "model": MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048,
            }
            if tools:
                kwargs["tools"] = tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

            response = await client.chat.completions.create(**kwargs)
            message = response.choices[0].message

            result: dict[str, Any] = {
                "role": message.role,
                "content": message.content,
            }

            if message.tool_calls:
                result["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ]

            return result

        except APITimeoutError as exc:
            if attempt < MAX_RETRIES:
                logger.warning("Groq timeout (attempt %d/%d), retrying...", attempt + 1, MAX_RETRIES + 1)
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                continue
            raise LlmTimeoutError() from exc

        except APIStatusError as exc:
            if attempt < MAX_RETRIES and exc.status_code >= 500:
                logger.warning("Groq server error %d (attempt %d/%d), retrying...", exc.status_code, attempt + 1, MAX_RETRIES + 1)
                await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                continue
            raise LlmApiError() from exc

        except Exception as exc:
            logger.error("Unexpected Groq error: %s", exc)
            raise LlmApiError() from exc

    raise LlmApiError()


def _mock_response(tool_name: str | None) -> dict[str, Any]:
    """Return a mock Groq response for development."""
    if tool_name == "tool_signal_harvester":
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "mock_call_1",
                    "type": "function",
                    "function": {
                        "name": "tool_signal_harvester",
                        "arguments": json.dumps({"company_name": "Acme Corp"}),
                    },
                }
            ],
        }
    elif tool_name == "tool_research_analyst":
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "mock_call_2",
                    "type": "function",
                    "function": {
                        "name": "tool_research_analyst",
                        "arguments": json.dumps({"signals": {}, "icp": "mock"}),
                    },
                }
            ],
        }
    elif tool_name == "tool_outreach_automated_sender":
        return {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "mock_call_3",
                    "type": "function",
                    "function": {
                        "name": "tool_outreach_automated_sender",
                        "arguments": json.dumps({"brief": "mock", "icp": "mock", "recipient": "test@test.com"}),
                    },
                }
            ],
        }

    return {"role": "assistant", "content": "Mock response"}
