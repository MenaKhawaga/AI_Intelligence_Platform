"""Hacker News collector.

Adapted in Phase 2 to the new architecture:
  - Returns app.collectors.base.CollectedItem instead of the old
    app.graph.state.NewsItem.
  - Retry now comes from app.collectors.base.async_retry.
  - Company detection / negative-content filtering (previously inline)
    removed -- that logic belongs to app/processing/entities.py and
    app/processing/filtering.py (Phase 3). This collector now returns
    every story it fetches, unfiltered and unenriched; points are still
    captured as the native `score` plus in `metadata`.
Search/query logic is otherwise unchanged from the original implementation.
"""

from __future__ import annotations

import logging
from typing import List

import httpx

from app.collectors.base import BaseCollector, CollectedItem, async_retry

logger = logging.getLogger(__name__)

# HN Search API for AI-related stories
HN_SEARCH_URL = "https://hn.algolia.com/api/v1/search"
KEYWORDS = [
    "AI",
    "machine learning",
    "LLM",
    "GPT",
    "neural",
    "transformer",
    "deep learning",
]


@async_retry(max_retries=3, backoff_factor=2, initial_delay=2)
async def fetch_hackernews() -> List[CollectedItem]:
    """Fetch top AI news from Hacker News."""
    items: List[CollectedItem] = []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            for keyword in KEYWORDS[:3]:  # Search top 3 keywords
                try:
                    response = await client.get(
                        HN_SEARCH_URL,
                        params={
                            "query": keyword,
                            "tags": "story",
                            "numericFilters": "points>50",
                            "hitsPerPage": 5,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                    for hit in data.get("hits", [])[:3]:
                        if hit.get("url"):
                            title = hit.get("title", "No title")
                            points = hit.get("points", 0)
                            num_comments = hit.get("num_comments", 0)
                            summary = f"Points: {points} | Comments: {num_comments}"

                            item = CollectedItem(
                                source_type="hackernews",
                                title=title,
                                url=hit.get("url", ""),
                                source=f"Hacker News ({keyword})",
                                summary=summary,
                                raw_text=hit.get("title", ""),
                                score=float(points),
                                metadata={
                                    "keyword": keyword,
                                    "points": points,
                                    "num_comments": num_comments,
                                },
                            )
                            items.append(item)

                except httpx.RequestError as e:
                    logger.error(f"HN API error for keyword '{keyword}': {e}")

    except Exception as e:
        logger.error(f"Error fetching Hacker News: {e}")

    logger.info(f"Collected {len(items)} items from Hacker News")
    return items


class HackerNewsCollector(BaseCollector):
    """Shared-interface wrapper around fetch_hackernews()."""

    source_type = "hackernews"

    async def _fetch(self) -> List[CollectedItem]:
        return await fetch_hackernews()
