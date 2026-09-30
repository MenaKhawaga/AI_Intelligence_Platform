"""Phase 3 — Processing pipeline: deduplication.

The same story routinely shows up more than once in one collection run --
an RSS feed and Hacker News both link the same article, or a GitHub repo
release also gets covered by a blog post. This stage collapses those into
a single item, deterministically:

  1. Exact match on the normalized URL (from normalization.py).
  2. Near-duplicate match on title text, using stdlib ``difflib`` string
     similarity -- no embeddings/ML, per the Phase 3 requirement to
     prefer simple deterministic methods.

When two items are merged, the one with the higher native engagement
``score`` is kept as canonical; the other's source is recorded on the
survivor (``duplicate_sources``) rather than silently discarded, so later
stages/readers can still see a story was multi-sourced.
"""

from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import List

from app.processing.normalization import ProcessedItem

logger = logging.getLogger(__name__)

# Titles this similar (0-1 scale) are treated as the same story.
TITLE_SIMILARITY_THRESHOLD = 0.87

_PUNCTUATION_RE = re.compile(r"[^\w\s]")


def _title_key(title: str) -> str:
    """Lowercased, punctuation-stripped title, for similarity comparison."""

    return _PUNCTUATION_RE.sub("", title.lower()).strip()


def title_similarity(a: str, b: str) -> float:
    """Ratio in [0, 1] of how similar two titles are, order-independent."""

    return SequenceMatcher(None, _title_key(a), _title_key(b)).ratio()


def _merge(keep: ProcessedItem, drop: ProcessedItem) -> None:
    """Fold ``drop`` into ``keep`` in place: record it as a duplicate source."""

    keep.duplicate_count += 1
    label = drop.source or drop.source_type
    if label not in keep.duplicate_sources:
        keep.duplicate_sources.append(label)
    # Carry over any duplicate sources drop had already absorbed.
    for label in drop.duplicate_sources:
        if label not in keep.duplicate_sources:
            keep.duplicate_sources.append(label)
    keep.duplicate_count += drop.duplicate_count


def _better(a: ProcessedItem, b: ProcessedItem) -> ProcessedItem:
    """Pick which of two duplicate items to keep as canonical.

    Higher native engagement score wins; ties fall back to whichever has
    the richer summary, so we keep the more informative copy.
    """

    if a.score != b.score:
        return a if a.score > b.score else b
    return a if len(a.summary) >= len(b.summary) else b


def deduplicate_items(items: List[ProcessedItem]) -> List[ProcessedItem]:
    """Collapse exact-URL and near-duplicate-title items. Stage 3 of the pipeline."""

    # Pass 1: exact URL match.
    by_url: dict[str, ProcessedItem] = {}
    order: List[str] = []
    for item in items:
        key = item.url
        if key in by_url:
            keep = _better(by_url[key], item)
            drop = item if keep is by_url[key] else by_url[key]
            _merge(keep, drop)
            by_url[key] = keep
        else:
            by_url[key] = item
            order.append(key)

    url_deduped = [by_url[key] for key in order]

    # Pass 2: near-duplicate titles across the remaining items (O(n^2), but
    # batches are small -- a single collection run, not a historical corpus).
    survivors: List[ProcessedItem] = []
    for item in url_deduped:
        match_index = None
        for idx, existing in enumerate(survivors):
            if title_similarity(item.title, existing.title) >= TITLE_SIMILARITY_THRESHOLD:
                match_index = idx
                break

        if match_index is None:
            survivors.append(item)
            continue

        existing = survivors[match_index]
        keep = _better(existing, item)
        drop = item if keep is existing else existing
        _merge(keep, drop)
        survivors[match_index] = keep

    removed = len(items) - len(survivors)
    logger.info(
        "Deduplicated %d item(s) -> %d unique (%d duplicate(s) merged)",
        len(items),
        len(survivors),
        removed,
    )
    return survivors
