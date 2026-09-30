"""GitHub Trending collector.

Adapted in Phase 2 to the new architecture:
  - Returns app.collectors.base.CollectedItem instead of the old
    app.graph.state.NewsItem.
  - Retry now comes from app.collectors.base.async_retry.
  - Company detection / negative-content filtering (previously inline)
    removed -- that logic belongs to app/processing/entities.py and
    app/processing/filtering.py (Phase 3). This collector now returns
    every trending repo it parses, unfiltered and unenriched; star count
    is still captured as the native `score` plus in `metadata`.
Scraping/parsing logic is otherwise unchanged from the original
implementation.
"""

from __future__ import annotations

import logging
from typing import List

import httpx
from bs4 import BeautifulSoup

from app.collectors.base import BaseCollector, CollectedItem, async_retry

logger = logging.getLogger(__name__)

GITHUB_TRENDING_URL = "https://github.com/trending"
AI_TOPICS = ["machine-learning", "deep-learning", "artificial-intelligence", "llm"]


@async_retry(max_retries=3, backoff_factor=2, initial_delay=2)
async def fetch_github_trending() -> List[CollectedItem]:
    """Fetch trending AI repositories from GitHub."""
    items: List[CollectedItem] = []

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Fetch main trending page
            response = await client.get(
                GITHUB_TRENDING_URL,
                params={"spoken_language_code": "en"},
                headers={"Accept": "application/vnd.github+json"},
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            repos = soup.find_all("article", class_="Box-row")

            for repo in repos[:10]:  # Get top 10
                try:
                    repo_link = repo.find("h2", class_="h3")
                    if not repo_link:
                        continue

                    href = repo_link.find("a")
                    if not href:
                        continue

                    repo_url = f"https://github.com{href.get('href', '')}"
                    repo_name = href.get("href", "").strip("/")

                    description = repo.find("p", class_="col-9")
                    description_text = (
                        description.get_text(strip=True) if description else ""
                    )

                    stars = repo.find("svg", class_="octicon-star")
                    stars_text = "0"
                    if stars:
                        stars_parent = stars.find_parent("a")
                        if stars_parent:
                            stars_text = stars_parent.get_text(strip=True).split()[0]

                    title = f"⭐ {repo_name} ({stars_text} stars)"
                    summary = description_text[:500]

                    try:
                        source_score = float(stars_text.replace(",", ""))
                    except ValueError:
                        source_score = 0.0

                    item = CollectedItem(
                        source_type="github",
                        title=title,
                        url=repo_url,
                        source="GitHub Trending",
                        summary=summary,
                        raw_text=f"{repo_name}: {description_text}",
                        score=source_score,
                        metadata={"repo_name": repo_name, "stars": source_score},
                    )
                    items.append(item)

                except Exception as e:
                    logger.warning(f"Error parsing GitHub repo: {e}")

    except Exception as e:
        logger.error(f"Error fetching GitHub trending: {e}")

    logger.info(f"Collected {len(items)} items from GitHub Trending")
    return items


# Backward compatibility alias
fetch_github = fetch_github_trending


class GitHubCollector(BaseCollector):
    """Shared-interface wrapper around fetch_github_trending()."""

    source_type = "github"

    async def _fetch(self) -> List[CollectedItem]:
        return await fetch_github_trending()
