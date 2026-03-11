"""
Signal Adapter — SerpAPI integration for buyer-intent signal harvesting.
All search logic lives here, nowhere else.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import httpx

from config import settings
from models import (
    SignalPayload,
    SignalApiError,
    SignalApiLimitError,
    SignalNotFoundError,
)

logger = logging.getLogger(__name__)

SERP_API_BASE = "https://serpapi.com/search.json"

# ── Mock fixture — zero SerpAPI calls when MOCK_MODE=true ───────────────────

MOCK_SIGNALS = SignalPayload(
    funding="Acme Corp raised $18M Series B led by Sequoia, March 2025.",
    leadership="Sarah Chen joined as CTO from Stripe, January 2025.",
    hiring="12 open engineering roles on LinkedIn focused on platform security.",
    social_mentions="Featured in TechCrunch 'Startups to Watch', 3.1K mentions this week.",
    tech_stack="Job postings reference AWS, Kubernetes, and active SOC2 compliance prep.",
    keyword_intent="High search volume for 'acme corp enterprise security' past 30 days.",
    news="Announced EMEA expansion and new enterprise tier, February 2025.",
    website_visits=None,     # Requires paid provider — e.g. 6sense, Bombora
    g2_surges=None,          # Requires paid provider — e.g. G2 Buyer Intent API
    competitor_churn=None,   # Requires paid provider — e.g. G2, Klue
    product_usage=None,      # Requires paid provider — e.g. Pendo, Amplitude
    source_urls=["https://techcrunch.com/mock", "https://linkedin.com/mock"],
    signal_count=7,
)


# ── SerpAPI query definitions ───────────────────────────────────────────────

def _build_queries(company: str) -> dict[str, str]:
    """Return mapping of signal field → search query string."""
    return {
        "funding": f"{company} funding round raised 2025",
        "leadership": f"{company} new CTO OR CEO OR VP hired 2025",
        "hiring": f"{company} hiring engineers jobs 2025",
        "social_mentions": f"{company} site:twitter.com OR site:techcrunch.com 2025",
        "tech_stack": f"{company} tech stack OR engineering blog 2025",
        "keyword_intent": f"{company} enterprise OR product OR search intent 2025",
        "news": f"{company} news announcement expansion 2025",
    }


async def _search(client: httpx.AsyncClient, query: str) -> tuple[Optional[str], list[str]]:
    """Execute a single SerpAPI search and extract the top organic snippet + link."""
    try:
        resp = await client.get(
            SERP_API_BASE,
            params={
                "q": query,
                "api_key": settings.SERP_API_KEY,
                "engine": "google",
                "num": 3,
            },
            timeout=15.0,
        )
        if resp.status_code == 429:
            raise SignalApiLimitError()
        if resp.status_code != 200:
            logger.warning("SerpAPI returned %s for query: %s", resp.status_code, query)
            return None, []

        data = resp.json()
        organic = data.get("organic_results", [])
        if not organic:
            return None, []

        top = organic[0]
        snippet = top.get("snippet", None)
        link = top.get("link", "")
        urls = [link] if link else []
        return snippet, urls

    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        logger.error("SerpAPI network error: %s", exc)
        raise SignalApiError() from exc


async def harvest_signals(company_name: str) -> SignalPayload:
    """
    Fetch buyer-intent signals for a target company.
    In MOCK_MODE, returns the fixture with zero external calls.
    """
    if settings.MOCK_MODE:
        logger.info("MOCK_MODE: returning fixture signals for '%s'", company_name)
        return MOCK_SIGNALS

    queries = _build_queries(company_name)
    results: dict[str, Optional[str]] = {}
    all_urls: list[str] = []

    async with httpx.AsyncClient() as client:
        tasks = {
            field: _search(client, query)
            for field, query in queries.items()
        }
        # Run all 6 searches concurrently
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)

        for field, result in zip(tasks.keys(), gathered):
            if isinstance(result, SignalApiLimitError):
                raise result
            if isinstance(result, SignalApiError):
                raise result
            if isinstance(result, Exception):
                logger.error("Unexpected error for %s: %s", field, result)
                results[field] = None
                continue
            snippet, urls = result
            results[field] = snippet
            all_urls.extend(urls)

    # The last query ("keyword_intent") actually maps to news/expansion.
    # Re-map to match the SignalPayload field names correctly.
    payload = SignalPayload(
        funding=results.get("funding"),
        leadership=results.get("leadership"),
        hiring=results.get("hiring"),
        social_mentions=results.get("social_mentions"),
        tech_stack=results.get("tech_stack"),
        keyword_intent=results.get("keyword_intent"),
        news=results.get("news"),
        website_visits=None,     # Requires paid provider — e.g. 6sense, Bombora
        g2_surges=None,          # Requires paid provider — e.g. G2 Buyer Intent API
        competitor_churn=None,   # Requires paid provider — e.g. G2, Klue
        product_usage=None,      # Requires paid provider — e.g. Pendo, Amplitude
        source_urls=list(set(all_urls)),
    )

    if payload.signal_count == 0:
        raise SignalNotFoundError()

    return payload
