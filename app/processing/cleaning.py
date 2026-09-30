"""Phase 3 — Processing pipeline: cleaning.

Strips HTML/boilerplate noise out of the free-text fields left by
normalization (``summary``, ``raw_text``) and drops items that are
malformed or empty -- e.g. a title-less GitHub payload, or an RSS entry
whose link failed to parse into a usable URL. Runs after normalization
(normalization.py) so it can rely on already-canonicalized URLs/titles,
and before deduplication/filtering/classification.

The original URL/title survive cleaning either way -- they were already
preserved by normalization in ``item.metadata["original_url"]`` /
``["original_title"]``.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.processing.normalization import ProcessedItem, normalize_whitespace

logger = logging.getLogger(__name__)

# Trailing boilerplate commonly appended by feeds/scrapers, stripped from
# the end of summary/raw_text. Case-insensitive, matched at end-of-string.
BOILERPLATE_PATTERNS = [
    re.compile(r"\s*read more\.?\s*$", re.IGNORECASE),
    re.compile(r"\s*continue reading\.?\s*$", re.IGNORECASE),
    re.compile(r"\s*\[…]\s*$"),
    re.compile(r"\s*\[\.\.\.\]\s*$"),
    re.compile(r"\s*the post .* appeared first on .*\.?\s*$", re.IGNORECASE),
    re.compile(r"\s*this article originally appeared on .*\.?\s*$", re.IGNORECASE),
]

MIN_TITLE_LENGTH = 3
ALLOWED_URL_SCHEMES = {"http", "https"}


def strip_html(text: Optional[str]) -> str:
    """Strip HTML tags, leaving readable text (RSS/Reddit bodies often
    ship as HTML fragments)."""

    if not text:
        return ""
    # BeautifulSoup is only asked to parse text once it looks tag-bearing,
    # so plain already-clean strings skip the parser entirely.
    if "<" not in text:
        return text
    soup = BeautifulSoup(text, "html.parser")
    return soup.get_text(separator=" ")


def strip_boilerplate(text: str) -> str:
    """Remove trailing feed/scraper boilerplate phrases from ``text``."""

    for pattern in BOILERPLATE_PATTERNS:
        text = pattern.sub("", text)
    return text


def clean_text(text: Optional[str]) -> str:
    """Full text-cleaning pipeline for one field: HTML -> boilerplate -> whitespace."""

    return normalize_whitespace(strip_boilerplate(strip_html(text)))


def is_valid_url(url: str) -> bool:
    """A URL is usable if it has an http(s) scheme and a host."""

    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in ALLOWED_URL_SCHEMES and bool(parsed.netloc)


def is_malformed(item: ProcessedItem) -> bool:
    """An item is malformed/empty if it has no usable title or URL."""

    if len(item.title) < MIN_TITLE_LENGTH:
        return True
    if not is_valid_url(item.url):
        return True
    return False


def clean_item(item: ProcessedItem) -> ProcessedItem:
    """Clean one item's free-text fields in place (returns the same item)."""

    item.summary = clean_text(item.summary)
    item.raw_text = clean_text(item.raw_text)
    return item


def clean_items(items: List[ProcessedItem]) -> List[ProcessedItem]:
    """Clean text fields and drop malformed/empty items. Stage 2 of the pipeline."""

    cleaned: List[ProcessedItem] = []
    dropped = 0
    for item in items:
        item = clean_item(item)
        if is_malformed(item):
            dropped += 1
            logger.debug(
                "Dropping malformed item (title=%r, url=%r)", item.title, item.url
            )
            continue
        cleaned.append(item)

    logger.info("Cleaned %d item(s), dropped %d malformed item(s)", len(cleaned), dropped)
    return cleaned
