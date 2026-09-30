"""Reddit collector.

Adapted in Phase 2 to the new architecture:
  - Returns app.collectors.base.CollectedItem instead of the old
    app.graph.state.NewsItem.
  - Retry now comes from app.collectors.base.async_retry.
  - Company detection / negative-content filtering (previously inline)
    removed -- that logic belongs to app/processing/entities.py and
    app/processing/filtering.py (Phase 3). This collector now returns
    every post it fetches, unfiltered and unenriched; upvotes are still
    captured as the native `score` plus in `metadata`.
Reddit credential handling (via app.config.settings) and subreddit-fetch
logic are otherwise unchanged from the original implementation.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List

import praw

from app.collectors.base import BaseCollector, CollectedItem, async_retry
from app.core.config import settings

logger = logging.getLogger(__name__)

# AI-focused subreddits
AI_SUBREDDITS = [
    "MachineLearning",
    "LanguageModels",
    "OpenAI",
    "LocalLLaMA",
    "Artificial",
    "deeplearning",
]


@async_retry(max_retries=3, backoff_factor=2, initial_delay=2)
async def fetch_reddit() -> List[CollectedItem]:
    """Fetch AI news from Reddit subreddits."""
    items: List[CollectedItem] = []

    try:
        # Check if Reddit credentials are configured
        if not settings.REDDIT_CLIENT_ID or not settings.REDDIT_CLIENT_SECRET:
            logger.warning(
                "Reddit credentials not configured. Skipping Reddit collection."
            )
            return items

        reddit = praw.Reddit(
            client_id=settings.REDDIT_CLIENT_ID
,
            client_secret=settings.REDDIT_CLIENT_SECRET,
            user_agent=settings.REDDIT_USER_AGENT,
        )

        for subreddit_name in AI_SUBREDDITS:
            try:
                logger.info(f"Fetching posts from r/{subreddit_name}")
                subreddit = reddit.subreddit(subreddit_name)

                # Get top posts from past day
                for post in subreddit.top(time_filter="day", limit=5):
                    title = post.title
                    summary = (
                        post.selftext[:500]
                        if post.selftext
                        else f"↑ {post.ups} | Comments: {post.num_comments}"
                    )

                    source_score = float(post.ups)

                    item = CollectedItem(
                        source_type="reddit",
                        title=title,
                        url=post.url
                        if post.url.startswith("http")
                        else f"https://reddit.com{post.permalink}",
                        source=f"Reddit (r/{subreddit_name})",
                        summary=summary,
                        published_at=datetime.fromtimestamp(post.created_utc),
                        raw_text=post.title,
                        score=source_score,
                        metadata={
                            "subreddit": subreddit_name,
                            "ups": post.ups,
                            "num_comments": post.num_comments,
                        },
                    )
                    items.append(item)

            except Exception as e:
                logger.error(f"Error fetching r/{subreddit_name}: {e}")

        logger.info(f"Collected {len(items)} items from Reddit")

    except Exception as e:
        logger.error(f"Error initializing Reddit API: {e}")

    return items


class RedditCollector(BaseCollector):
    """Shared-interface wrapper around fetch_reddit()."""

    source_type = "reddit"

    async def _fetch(self) -> List[CollectedItem]:
        return await fetch_reddit()
