"""Shared collector interface.

Every collector (RSS, GitHub, Hacker News, arXiv, Reddit) returns a list of
``CollectedItem`` -- the one consistent, source-agnostic shape the future
processing pipeline (Phase 3: normalization, cleaning, deduplication,
filtering, classification, entity extraction, ranking) will consume.

Collectors deliberately do NOT classify, deduplicate, score for importance,
detect companies/entities, or filter out low-quality/negative content
themselves -- that is the processing pipeline's job (Phase 3). A
collector's only responsibilities are: fetch from its source, map results
to ``CollectedItem``, retry transient failures, and never let an exception
escape ``collect()``, since one dead source should not take down a whole
collection run.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, List, Optional, TypeVar

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CollectedItem(BaseModel):
    """The one consistent shape every collector returns.

    Intentionally "raw": no company, category, importance score, or tags
    here -- those are outputs of app/processing/ (Phase 3), not of
    collection. Anything source-specific that doesn't fit a common field
    (an arXiv id, a subreddit name, a comment count, ...) goes in
    ``metadata`` so the processing pipeline can still get at it.
    """

    source_type: str  # "rss" | "github" | "hackernews" | "arxiv" | "reddit"
    source: str  # human-readable origin, e.g. "Hacker News (LLM)"
    title: str
    url: str
    summary: str = ""
    raw_text: str = ""
    score: float = 0.0  # native source signal: stars / points / upvotes
    published_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


def async_retry(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Retry an async function on exception, with exponential backoff.

    Drop-in replacement for the old (non-existent-in-this-architecture)
    ``app.utils.retry.async_retry`` -- kept with the same signature so the
    existing collector call sites (``@async_retry(max_retries=3, ...)``)
    only needed their import fixed, not their retry parameters.
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = initial_delay
            last_exc: Optional[BaseException] = None
            for attempt in range(1, max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:  # noqa: BLE001 - intentionally broad:
                    # this is a generic retry wrapper shared by collectors that
                    # each raise different provider-specific exceptions
                    # (httpx, praw, XML parsing, ...).
                    last_exc = exc
                    if attempt == max_retries:
                        logger.error(
                            "%s failed after %d attempt(s): %s",
                            func.__name__,
                            attempt,
                            exc,
                        )
                        break
                    logger.warning(
                        "%s failed on attempt %d/%d: %s -- retrying in %.1fs",
                        func.__name__,
                        attempt,
                        max_retries,
                        exc,
                        delay,
                    )
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


class BaseCollector(ABC):
    """Shared interface every source collector implements.

    Subclasses implement ``_fetch()`` with their source-specific logic and
    get uniform error handling, start/finish logging, and a
    guaranteed-list return from ``collect()`` for free. This is the
    interface future orchestration (the scheduler in Phase 5/12, the
    LangGraph collection node in Phase 6) will call against -- it does not
    replace each collector's existing ``fetch_*`` function, it wraps it.
    """

    #: Overridden by each subclass, e.g. "rss", "github", "hackernews".
    source_type: str = "unknown"

    @abstractmethod
    async def _fetch(self) -> List[CollectedItem]:
        """Source-specific fetch logic. May raise; ``collect()`` will not."""

        raise NotImplementedError

    async def collect(self) -> List[CollectedItem]:
        """Run ``_fetch()`` with a top-level safety net, and always return a list."""

        logger.info("Starting collection: %s", self.source_type)
        try:
            items = await self._fetch()
        except Exception as exc:  # noqa: BLE001 - see class docstring
            logger.error("Collector '%s' failed: %s", self.source_type, exc)
            return []
        logger.info(
            "Finished collection: %s (%d items)", self.source_type, len(items)
        )
        return items
