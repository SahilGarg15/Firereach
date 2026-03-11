"""
Groq function-calling tool schemas for the three FireReach tools.
These are passed to the Groq API as the `tools` parameter.
"""

TOOL_SIGNAL_HARVESTER = {
    "type": "function",
    "function": {
        "name": "tool_signal_harvester",
        "description": (
            "Fetches live, deterministic buyer intent signals for a target company "
            "from real search APIs. Always call this first. Never infer or guess signal data."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "The name of the target company to harvest signals for.",
                },
            },
            "required": ["company_name"],
        },
    },
}

TOOL_RESEARCH_ANALYST = {
    "type": "function",
    "function": {
        "name": "tool_research_analyst",
        "description": (
            "Synthesizes harvested signals and the seller's ICP into a 2-paragraph "
            "Account Brief. Paragraph 1: company growth context and pain points derived "
            "from signals. Paragraph 2: strategic alignment between the signals and the "
            "ICP value proposition."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "signals": {
                    "type": "object",
                    "description": "The full SignalPayload JSON from tool_signal_harvester.",
                },
                "icp": {
                    "type": "string",
                    "description": "The seller's Ideal Customer Profile description.",
                },
            },
            "required": ["signals", "icp"],
        },
    },
}

TOOL_OUTREACH_AUTOMATED_SENDER = {
    "type": "function",
    "function": {
        "name": "tool_outreach_automated_sender",
        "description": (
            "Transforms the account brief into a hyper-personalized outreach email "
            "that explicitly references harvested signals, then automatically dispatches "
            "it via Resend email API. The email must reference specific facts from the signals "
            "— no generic templates."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "brief": {
                    "type": "string",
                    "description": "The account brief from tool_research_analyst.",
                },
                "icp": {
                    "type": "string",
                    "description": "The seller's ICP description.",
                },
                "recipient": {
                    "type": "string",
                    "description": "The recipient email address.",
                },
            },
            "required": ["brief", "icp", "recipient"],
        },
    },
}
