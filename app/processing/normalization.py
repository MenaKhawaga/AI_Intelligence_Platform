"""Phase 3 — Processing pipeline: normalization.

Takes the raw, source-shaped ``List[CollectedItem]`` produced by the
collectors (RSS, GitHub, Hacker News, arXiv, Reddit) and turns it into a
consistent internal shape every later stage (cleaning, deduplication,
filtering, classification, entity extraction, ranking) can rely on --
same casing/whitespace conventions for text, a canonical URL form, and
timezone-aware timestamps, regardless of which collector produced the
item.

This module also defines ``ProcessedItem``, the model the rest of
app/processing/ passes around. It is a strict superset of
``CollectedItem`` (see app/collectors/base.py) -- every field collectors
already populate is kept as-is, and the later stages only ever *add*
fields (categories, entities, relevance_score, ...) rather than
replacing the collector-facing shape.
"""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import Field

from app.collectors.base import CollectedItem

logger = logging.getLogger(__name__)

# Query params that carry no meaning for identifying/deduplicating a link,
# just analytics noise picked up from RSS/social links.
TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "utm_name",
    "gclid",
    "fbclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "ref_src",
    "igshid",
    "spm",
}

_WHITESPACE_RE = re.compile(r"\s+")


class ProcessedItem(CollectedItem):
    """``CollectedItem`` plus everything the processing pipeline adds.

    Every field below defaults so a ``ProcessedItem`` can be constructed
    from a bare ``CollectedItem`` at the start of the pipeline and filled
    in stage by stage; nothing here is required.
    """

    # --- deduplication (deduplication.py) ---------------------------------
    duplicate_count: int = 0  # how many raw items were merged into this one
    duplicate_sources: List[str] = Field(default_factory=list)

    # --- classification (classification.py) -------------------------------
    categories: List[str] = Field(default_factory=list)
    primary_category: Optional[str] = None

    # --- entities (entities.py) --------------------------------------------
    entities: Dict[str, List[str]] = Field(default_factory=dict)

    # --- ranking (ranking.py) -----------------------------------------------
    relevance_score: float = 0.0
    score_breakdown: Dict[str, float] = Field(default_factory=dict)

    @classmethod
    def from_collected(cls, item: CollectedItem) -> "ProcessedItem":
        """Wrap a plain ``CollectedItem`` (or another ``ProcessedItem``) up."""

        return cls(**item.model_dump())


def normalize_whitespace(text: Optional[str]) -> str:
    """Collapse all whitespace runs to single spaces and strip the ends.

    Also unescapes HTML entities (``&amp;`` -> ``&``) since these show up
    routinely in RSS/Atom titles and summaries.
    """

    if not text:
        return ""
    text = html.unescape(text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_title(title: Optional[str]) -> str:
    """Normalize a title: whitespace/entity cleanup only.

    Deliberately does not change case or punctuation -- titles are
    user-facing, so normalization here is about consistency (no stray
    newlines/double spaces/HTML entities from feed XML), not rewriting.
    """

    return normalize_whitespace(title)


def normalize_url(url: Optional[str]) -> str:
    """Canonicalize a URL for consistent comparison/deduplication.

    - Adds an ``https://`` scheme if one is missing but the string looks
      like a bare domain (some RSS feeds/GitHub payloads omit it).
    - Lowercases the scheme and host (hosts are case-insensitive; paths
      are not, so those are left alone).
    - Drops the fragment (``#...``) and known tracking query params.
    - Drops a single trailing slash on the path (but keeps `/` for the
      bare root) so ``/post`` and ``/post/`` dedupe as the same page.
    """

    if not url:
        return ""

    url = url.strip()
    if url and "://" not in url:
        url = f"https://{url}"

    try:
        parsed = urlparse(url)
    except ValueError:
        logger.warning("Could not parse URL %r during normalization", url)
        return url

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    path = parsed.path
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")

    kept_params = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS
    ]
    query = urlencode(sorted(kept_params))

    return urlunparse((scheme, netloc, path, parsed.params, query, ""))


def normalize_timestamp(value: Optional[datetime]) -> Optional[datetime]:
    """Make a timestamp timezone-aware UTC, assuming naive timestamps are UTC.

    Returns ``None`` unchanged -- an unknown publish time stays unknown
    rather than being guessed at here (recency scoring in ranking.py
    handles the missing case explicitly).
    """

    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_source_metadata(item: CollectedItem) -> Dict[str, Any]:
    """Return a copy of ``item.metadata`` plus the pre-normalization URL.

    Keeping ``original_url`` means cleaning/deduplication/debugging can
    always recover exactly what the collector returned, even after the
    URL has been canonicalized for comparison.
    """

    metadata = dict(item.metadata)
    metadata.setdefault("original_url", item.url)
    metadata.setdefault("original_title", item.title)
    return metadata


def normalize_item(item: CollectedItem) -> ProcessedItem:
    """Normalize a single ``CollectedItem`` into a ``ProcessedItem``."""

    processed = ProcessedItem.from_collected(item)
    processed.source_type = normalize_whitespace(item.source_type).lower()
    processed.source = normalize_whitespace(item.source)
    processed.title = normalize_title(item.title)
    processed.url = normalize_url(item.url)
    processed.summary = normalize_whitespace(item.summary)
    processed.raw_text = normalize_whitespace(item.raw_text)
    processed.published_at = normalize_timestamp(item.published_at)
    processed.collected_at = normalize_timestamp(item.collected_at) or item.collected_at
    processed.metadata = normalize_source_metadata(item)
    return processed


def normalize_items(items: List[CollectedItem]) -> List[ProcessedItem]:
    """Normalize a batch of collected items. Stage 1 of the pipeline."""

    normalized = [normalize_item(item) for item in items]
    logger.info("Normalized %d item(s)", len(normalized))
    return normalized
