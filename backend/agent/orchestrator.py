"""
Agent Orchestrator — Groq function-calling loop with tool gating,
confidence-gated sending, and SSE event generation.

The orchestrator enforces Signal → Research → Send by offering only
one tool per LLM call. The agent cannot call tools out of order because
the tool it would want is not offered.
"""

from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator

from adapters import signal_adapter, llm_adapter, mail_adapter
from agent.tools import (
    TOOL_SIGNAL_HARVESTER,
    TOOL_RESEARCH_ANALYST,
    TOOL_OUTREACH_AUTOMATED_SENDER,
)
from config import settings
from models import (
    FireReachError,
    SignalPayload,
    TemplateViolationError,
)

logger = logging.getLogger(__name__)

# ── System Prompt ───────────────────────────────────────────────────────────

SYSTEM_PERSONA = (
    "You are FireReach, an autonomous B2B outreach agent. You are precise "
    "and data-driven. You treat unverified information as a liability."
)

SYSTEM_CONSTRAINTS = (
    "You NEVER guess, infer, or hallucinate company signals. If "
    "tool_signal_harvester returns no data, you report failure — you do not "
    "invent signals.\n\n"
    "You NEVER write generic outreach. Every email must explicitly reference "
    "at least 2 specific facts from the harvested signals.\n\n"
    "You MUST follow this exact execution order:\n"
    "  Step 1 → call tool_signal_harvester\n"
    "  Step 2 → call tool_research_analyst\n"
    "  Step 3 → call tool_outreach_automated_sender\n\n"
    "You do not skip steps. You do not proceed if a prior step returned an "
    "error. You do not explain what you are about to do. You act."
)

SYSTEM_PROMPT = f"{SYSTEM_PERSONA}\n\n{SYSTEM_CONSTRAINTS}"


# ── Confidence Gate Scoring ─────────────────────────────────────────────────

def score_email(email_body: str, signals: SignalPayload) -> int:
    """
    Score how well an email references actual signal data.
    Returns 0-100 based on keyword overlap between signals and email body.
    """
    # Collect all non-None signal text fields
    signal_facts = [
        s for s in [
            signals.funding, signals.leadership, signals.hiring,
            signals.social_mentions, signals.tech_stack,
            signals.keyword_intent, signals.news,
        ] if s
    ]
    if not signal_facts:
        return 0

    # Extract top 8 meaningful keywords (>3 chars) from each signal
    keywords = []
    for fact in signal_facts:
        words = [w.strip(".,()[]'\"!?:;").lower() for w in fact.split() if len(w.strip(".,()[]'\"!?:;")) > 3]
        keywords.extend(words[:8])

    # Count how many keywords appear in the email body
    email_lower = email_body.lower()
    matches = sum(1 for kw in keywords if kw in email_lower)

    # Scale to 0-100 with a 1.5x multiplier (partial matches still score well)
    return min(100, int((matches / max(len(keywords), 1)) * 100 * 1.5))


# ── SSE Helpers ─────────────────────────────────────────────────────────────

def _sse(event: str, data: dict) -> str:
    """Format a server-sent event string."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


# ── Orchestrator ────────────────────────────────────────────────────────────

async def run_agent(
    run_id: str,
    company_name: str,
    icp: str,
    recipient: str,
) -> AsyncGenerator[str, None]:
    """
    Execute the 3-step agent pipeline as an async SSE generator.

    Tool gating: each LLM call receives ONLY the tool it should call.
    Context passing: each step injects its output into the next call's messages.
    """
    start_time = time.time()

    try:
        # ── STEP 1: Signal Harvesting ───────────────────────────────────────
        yield _sse("step_update", {"step": 1, "status": "running", "label": "Harvesting signals..."})

        # LLM call 1: tools list contains ONLY tool_signal_harvester
        messages_step1 = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Find buyer intent signals for the company: {company_name}"},
        ]

        llm_response_1 = await llm_adapter.chat_completion(
            messages=messages_step1,
            tools=[TOOL_SIGNAL_HARVESTER],
            tool_choice="required",
            mock_tool_name="tool_signal_harvester",
        )

        # Execute the signal harvest
        signals = await signal_adapter.harvest_signals(company_name)
        signals_dict = signals.model_dump()

        yield _sse("step_complete", {"step": 1, "status": "done", "payload": signals_dict})

        # ── STEP 2: Research Analyst ────────────────────────────────────────
        yield _sse("step_update", {"step": 2, "status": "running", "label": "Building account brief..."})

        # LLM call 2: tools list contains ONLY tool_research_analyst
        # Inject signals JSON into user message content
        messages_step2 = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Here are the harvested signals for {company_name}:\n"
                    f"{json.dumps(signals_dict, indent=2)}\n\n"
                    f"The seller's ICP is: {icp}\n\n"
                    f"Synthesize these signals into a 2-paragraph Account Brief.\n"
                    f"Paragraph 1: Pain Points & Growth Context — what is happening at this company right now, "
                    f"derived from the signals above.\n"
                    f"Paragraph 2: Strategic Alignment — why this company is a high-priority target, mapping "
                    f"specific signals to the ICP value proposition.\n"
                    f"Reference specific facts from the signals. No generic statements."
                ),
            },
        ]

        llm_response_2 = await llm_adapter.chat_completion(
            messages=messages_step2,
            tools=[TOOL_RESEARCH_ANALYST],
            tool_choice="required",
            mock_tool_name="tool_research_analyst",
        )

        # Extract the brief — in mock mode use the fixture, otherwise parse from tool call
        if settings.MOCK_MODE:
            brief = llm_adapter.MOCK_BRIEF
        else:
            # The LLM should have called tool_research_analyst
            # We execute it by making another LLM call with the tool result
            tool_call_2 = llm_response_2.get("tool_calls", [{}])[0]
            tool_call_id_2 = tool_call_2.get("id", "")

            # Now make the actual brief generation call
            messages_step2_exec = messages_step2 + [
                llm_response_2,
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id_2,
                    "content": (
                        f"Signals data: {json.dumps(signals_dict)}\n"
                        f"ICP: {icp}\n\n"
                        f"Now write the 2-paragraph Account Brief. "
                        f"Paragraph 1: Pain Points & Growth Context. "
                        f"Paragraph 2: Strategic Alignment. "
                        f"Reference specific facts from the signals. No generic statements."
                    ),
                },
            ]
            brief_response = await llm_adapter.chat_completion(
                messages=messages_step2_exec,
            )
            brief = brief_response.get("content", "")

            if not brief:
                # Auto-retry once (PRD Flow B)
                logger.warning("Brief generation returned empty, retrying...")
                brief_response = await llm_adapter.chat_completion(
                    messages=messages_step2_exec,
                )
                brief = brief_response.get("content", "")
                if not brief:
                    raise FireReachError(
                        code="LLM_API_ERROR",
                        status_code=502,
                        message="AI service error. Try again.",
                    )

        yield _sse("step_complete", {"step": 2, "status": "done", "payload": {"brief": brief}})

        # ── STEP 3: Outreach Email Generation + Sending ─────────────────────
        yield _sse("step_update", {"step": 3, "status": "running", "label": "Sending email..."})

        email_subject, email_body = await _generate_email(
            signals=signals,
            signals_dict=signals_dict,
            brief=brief,
            icp=icp,
            recipient=recipient,
            company_name=company_name,
        )

        # ── Confidence Gate ─────────────────────────────────────────────────
        score = score_email(email_body, signals)
        logger.info("Email confidence score: %d/100", score)

        if score < 30:
            # Regenerate once with stricter prompt
            signal_facts = [
                s for s in [
                    signals.funding, signals.leadership, signals.hiring,
                    signals.social_mentions, signals.tech_stack,
                    signals.keyword_intent, signals.news,
                ] if s
            ]
            email_subject, email_body = await _generate_email(
                signals=signals,
                signals_dict=signals_dict,
                brief=brief,
                icp=icp,
                recipient=recipient,
                company_name=company_name,
                strict_retry=True,
                signal_facts=signal_facts,
            )
            score = score_email(email_body, signals)
            logger.info("Regenerated email confidence score: %d/100", score)

            if score < 30:
                raise TemplateViolationError()

        if score >= 60:
            # Auto-send
            send_result = await mail_adapter.send(
                recipient=recipient,
                subject=email_subject,
                body=email_body,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            yield _sse("step_complete", {
                "step": 3,
                "status": "sent",
                "payload": {
                    "subject": email_subject,
                    "body": email_body,
                    "sent_at": send_result["sent_at"],
                    "score": score,
                    "message_id": send_result["message_id"],
                },
            })
        else:
            # Score 30-59: review required
            duration_ms = int((time.time() - start_time) * 1000)
            yield _sse("review_required", {
                "type": "review_required",
                "subject": email_subject,
                "body": email_body,
                "score": score,
                "run_id": run_id,
            })

        duration_ms = int((time.time() - start_time) * 1000)
        yield _sse("done", {"run_id": run_id, "total_duration_ms": duration_ms})

    except FireReachError as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        error_data = {"step": _current_step(exc), "code": exc.code, "message": exc.message}
        if exc.payload:
            error_data["payload"] = exc.payload
        yield _sse("error", error_data)
        yield _sse("done", {"run_id": run_id, "total_duration_ms": duration_ms})

    except Exception as exc:
        logger.exception("Unexpected error in orchestrator")
        duration_ms = int((time.time() - start_time) * 1000)
        yield _sse("error", {
            "step": 0,
            "code": "LLM_API_ERROR",
            "message": "AI service error. Try again.",
        })
        yield _sse("done", {"run_id": run_id, "total_duration_ms": duration_ms})


async def _generate_email(
    signals: SignalPayload,
    signals_dict: dict,
    brief: str,
    icp: str,
    recipient: str,
    company_name: str,
    strict_retry: bool = False,
    signal_facts: list[str] | None = None,
) -> tuple[str, str]:
    """Generate an outreach email via LLM or mock fixtures."""
    if settings.MOCK_MODE and not strict_retry:
        return llm_adapter.MOCK_EMAIL_SUBJECT, llm_adapter.MOCK_EMAIL_BODY

    strict_addendum = ""
    if strict_retry and signal_facts:
        strict_addendum = (
            "\n\nThe previous email did not reference enough signal facts. "
            "You MUST reference at least 3 of these specific facts verbatim: "
            f"{json.dumps(signal_facts)}. Do not use any generic phrases."
        )

    # LLM call 3: tools list contains ONLY tool_outreach_automated_sender
    messages_step3 = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"Here are the harvested signals for {company_name}:\n"
                f"{json.dumps(signals_dict, indent=2)}\n\n"
                f"Here is the Account Brief:\n{brief}\n\n"
                f"The seller's ICP is: {icp}\n"
                f"The recipient email is: {recipient}\n\n"
                f"Generate a hyper-personalized outreach email that explicitly references "
                f"at least 2 specific facts from the harvested signals. No generic templates. "
                f"The email should connect the company's current situation to the seller's value proposition.\n\n"
                f"Return your response as JSON with exactly two keys: "
                f'"subject" (string) and "body" (string).{strict_addendum}'
            ),
        },
    ]

    llm_response_3 = await llm_adapter.chat_completion(
        messages=messages_step3,
        tools=[TOOL_OUTREACH_AUTOMATED_SENDER],
        tool_choice="required",
        mock_tool_name="tool_outreach_automated_sender",
    )

    if settings.MOCK_MODE:
        return llm_adapter.MOCK_EMAIL_SUBJECT, llm_adapter.MOCK_EMAIL_BODY

    # The LLM called tool_outreach_automated_sender — now we need to get the actual email content
    tool_call_3 = llm_response_3.get("tool_calls", [{}])[0]
    tool_call_id_3 = tool_call_3.get("id", "")

    # Execute: ask LLM to produce the email text
    messages_step3_exec = messages_step3 + [
        llm_response_3,
        {
            "role": "tool",
            "tool_call_id": tool_call_id_3,
            "content": (
                f"Generate the outreach email now. "
                f"Use these signals: {json.dumps(signals_dict)}\n"
                f"Account brief: {brief}\n"
                f"ICP: {icp}\n"
                f"Return ONLY a JSON object with 'subject' and 'body' keys. "
                f"The email must reference at least 2 specific signal facts.{strict_addendum}"
            ),
        },
    ]

    email_response = await llm_adapter.chat_completion(messages=messages_step3_exec)
    email_content = email_response.get("content", "")

    # Parse the JSON response
    try:
        # Try to extract JSON from the response
        email_json = _extract_json(email_content)
        return email_json.get("subject", "Outreach Email"), email_json.get("body", email_content)
    except (json.JSONDecodeError, ValueError):
        # If JSON parsing fails, use the raw content
        return f"Outreach to {company_name}", email_content


def _extract_json(text: str) -> dict:
    """Extract a JSON object from text that may contain markdown code fences."""
    text = text.strip()
    # Remove markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return json.loads(text)


def _current_step(exc: FireReachError) -> int:
    """Infer which step an error occurred in based on the error code."""
    code = exc.code
    if code.startswith("SIGNAL"):
        return 1
    if code.startswith("LLM"):
        return 2
    if code.startswith("EMAIL") or code == "TEMPLATE_VIOLATION":
        return 3
    return 0
