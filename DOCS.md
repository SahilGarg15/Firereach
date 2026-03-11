# FireReach — Technical Documentation

## Section 1 — Logic Flow

### How the Agent Ensures Outreach is Grounded in Harvested Signals

FireReach uses a three-layer enforcement strategy to guarantee every outreach email is grounded in real, harvested signal data — never fabricated or generic content.

#### Layer 1: Tool Gating (Design-Level Enforcement)

The orchestrator (`agent/orchestrator.py`) enforces the execution order **Signal → Research → Send** through tool gating. On each LLM call, the Groq API receives **only one tool** in its `tools` parameter:

- **LLM Call 1:** `tools` contains only `tool_signal_harvester`. The agent cannot skip to research or email because those tools are not offered.
- **LLM Call 2:** `tools` contains only `tool_research_analyst`. The signals JSON is injected into the user message content.
- **LLM Call 3:** `tools` contains only `tool_outreach_automated_sender`. Both signals JSON and the account brief are injected into the user message content.

All three calls use `tool_choice="required"`, forcing the agent to invoke the tool rather than respond with plain text.

This is enforcement by design — the agent cannot call tools out of order because the tool it would want is not offered.

#### Layer 2: Context Passing (Data-Level Enforcement)

No external state or database is used. Each step injects its output directly into the next LLM call's user message:

1. Step 1 produces a `SignalPayload` object.
2. Step 2 receives the full signals JSON in its user message and produces an Account Brief.
3. Step 3 receives both the signals JSON and the brief text in its user message.

The LLM cannot reference data it hasn't received. If signals are thin, the brief is thin, and the email is thin. There is no padding with invented context.

#### Layer 3: Confidence Gate (Code-Level Enforcement)

Even with strong prompting and tool gating, an LLM can produce generic output. The confidence gate (`score_email()` function in `orchestrator.py`) enforces the zero-template policy at the code level with a measurable score:

1. It extracts meaningful keywords (>3 characters, i.e. 4+ chars) from each non-None signal field (up to 8 keywords per signal).
2. It counts how many of those keywords appear in the generated email body.
3. It produces a 0-100 score with a 1.5x multiplier.

Based on the score:
- **≥ 60:** Email auto-sends. The system prompt was effective.
- **30-59:** Email is held for human review. The frontend shows a preview with a "Confirm Send" button.
- **< 30:** Email is regenerated once with a stricter prompt. If still below 30, the run fails with `TEMPLATE_VIOLATION`.

This triple-layered approach ensures grounding at the design level (tool gating), data level (context injection), and code level (confidence scoring).

---

## Section 2 — Tool Schemas

### tool_signal_harvester

| Property | Value |
|----------|-------|
| **Name** | `tool_signal_harvester` |
| **Description** | Fetches live, deterministic buyer intent signals for a target company from real search APIs. Always call this first. Never infer or guess signal data. |

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `company_name` | string | Yes | The name of the target company to harvest signals for. |

**Returns:** `SignalPayload` object containing up to 11 signal fields, source URLs, and a signal count.

---

### tool_research_analyst

| Property | Value |
|----------|-------|
| **Name** | `tool_research_analyst` |
| **Description** | Synthesizes harvested signals and the seller's ICP into a 2-paragraph Account Brief. Paragraph 1: company growth context and pain points derived from signals. Paragraph 2: strategic alignment between the signals and the ICP value proposition. |

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `signals` | object | Yes | The full SignalPayload JSON from tool_signal_harvester. |
| `icp` | string | Yes | The seller's Ideal Customer Profile description. |

**Returns:** A 2-paragraph Account Brief string.

---

### tool_outreach_automated_sender

| Property | Value |
|----------|-------|
| **Name** | `tool_outreach_automated_sender` |
| **Description** | Transforms the account brief into a hyper-personalized outreach email that explicitly references harvested signals, then automatically dispatches it via Gmail SMTP. The email must reference specific facts from the signals — no generic templates. |

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `brief` | string | Yes | The account brief from tool_research_analyst. |
| `icp` | string | Yes | The seller's ICP description. |
| `recipient` | string | Yes | The recipient email address. |

**Returns:** JSON object with `subject` and `body` keys. The email is automatically dispatched via Gmail SMTP after passing the confidence gate.

---

## Section 3 — System Prompt

### PERSONA

```
You are FireReach, an autonomous B2B outreach agent. You are precise and data-driven. You treat unverified information as a liability.
```

### CONSTRAINTS

```
You NEVER guess, infer, or hallucinate company signals. If tool_signal_harvester returns no data, you report failure — you do not invent signals.

You NEVER write generic outreach. Every email must explicitly reference at least 2 specific facts from the harvested signals.

You MUST follow this exact execution order:
  Step 1 → call tool_signal_harvester
  Step 2 → call tool_research_analyst
  Step 3 → call tool_outreach_automated_sender

You do not skip steps. You do not proceed if a prior step returned an error. You do not explain what you are about to do. You act.
```

---

## Section 4 — Confidence Gate (Unique Solution)

### Scoring Algorithm

The `score_email()` function in `orchestrator.py` computes a grounding score (0-100) for every generated email:

1. **Collect signal facts:** Gather all non-None text values from the 7 fetchable signal fields (funding, leadership, hiring, social_mentions, tech_stack, keyword_intent, news).

2. **Extract keywords:** From each signal fact, extract up to 5 meaningful words (longer than 4 characters), stripping punctuation. This produces a keyword pool representing the company's real signal data.

3. **Count matches:** Check how many of those keywords appear in the email body (case-insensitive).

4. **Compute score:** `score = min(100, int((matches / total_keywords) * 100 * 1.5))`. The 1.5x multiplier ensures that referencing a reasonable subset of signals (rather than all of them) still produces a passing score.

### Gate Outcomes

| Score Range | Outcome | What Happens |
|-------------|---------|--------------|
| **≥ 60** | Auto-send | `mail_adapter.send()` is called automatically. The email is dispatched and the user sees a green score badge. |
| **30–59** | Review required | The email is NOT sent. A `review_required` SSE event is emitted. The frontend shows the email preview with a yellow score badge and a "Confirm Send" button. The user can review and manually confirm. |
| **< 30** | Regenerate | The email is regenerated once with a stricter prompt that demands at least 3 verbatim signal facts. The new email is re-scored. If still < 30: the run fails with `TEMPLATE_VIOLATION`. |

### Why This Enforces Zero-Template Policy at the Code Level

The system prompt instructs the LLM to reference specific signals. But prompts can fail — the LLM might produce plausible-sounding but generic copy. The confidence gate:

1. **Measures** whether the email actually contains signal-specific content (not just asks the LLM to include it).
2. **Gates** the send action on a measurable threshold (not just LLM compliance).
3. **Provides** a visible, quantified score in the UI so the user can see exactly how grounded the email is.

This converts a soft prompt constraint ("reference signals") into a hard code constraint (score ≥ 60 to auto-send). Generic emails physically cannot pass the gate because they won't contain enough signal-specific keywords.

---

## Appendix — Rabbitt Challenge Expected Output

**Input:**
- ICP: "We sell high-end cybersecurity training to Series B startups."
- Company: "Acme Corp"

**Expected Agent Behavior:**

1. `tool_signal_harvester` returns: funding ($18M Series B), leadership (new CTO from Stripe), hiring (12 engineering roles), social mentions (TechCrunch feature), tech stack (AWS, Kubernetes, SOC2), keyword intent (high search volume), news (EMEA expansion).

2. `tool_research_analyst` produces a brief where:
   - Paragraph 1 references Series B funding, 12 hires, SOC2 prep, EMEA expansion.
   - Paragraph 2 connects security training need to scaling engineering team, compliance deadlines, and expanding attack surface.

3. `tool_outreach_automated_sender` generates an email referencing specific facts: "you closed a Series B...hiring 12 engineers...SOC2 compliance prep..."

4. Confidence gate scores ≥ 60 → auto-send.

5. Email delivered to recipient inbox.
