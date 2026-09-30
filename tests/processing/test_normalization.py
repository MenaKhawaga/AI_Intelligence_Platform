"""Tests for app.processing.normalization."""

from __future__ import annotations

from datetime import datetime, timezone

from app.collectors.base import CollectedItem
from app.processing.normalization import (
    ProcessedItem,
    normalize_items,
    normalize_timestamp,
    normalize_title,
    normalize_url,
    normalize_whitespace,
)


def test_normalize_whitespace_collapses_and_unescapes():
    assert normalize_whitespace("  Hello   world \n\t") == "Hello world"
    assert normalize_whitespace("Tom &amp; Jerry") == "Tom & Jerry"
    assert normalize_whitespace(None) == ""
    assert normalize_whitespace("") == ""


def test_normalize_title_strips_and_cleans():
    assert normalize_title("  New   GPT-4o &amp; friends  ") == "New GPT-4o & friends"


def test_normalize_url_adds_scheme_and_lowercases_host():
    assert normalize_url("Example.com/Path") == "https://example.com/Path"


def test_normalize_url_strips_tracking_params_and_fragment():
    url = "https://Example.com/a/?utm_source=hn&ref=x&keep=1#section"
    assert normalize_url(url) == "https://example.com/a?keep=1"


def test_normalize_url_drops_trailing_slash_but_keeps_root():
    assert normalize_url("https://example.com/post/") == "https://example.com/post"
    assert normalize_url("https://example.com/") == "https://example.com/"


def test_normalize_url_empty_input():
    assert normalize_url("") == ""
    assert normalize_url(None) == ""


def test_normalize_timestamp_assumes_utc_for_naive():
    naive = datetime(2026, 1, 1, 12, 0, 0)
    result = normalize_timestamp(naive)
    assert result.tzinfo is not None
    assert result.utcoffset().total_seconds() == 0


def test_normalize_timestamp_none_stays_none():
    assert normalize_timestamp(None) is None


def test_normalize_items_produces_processed_items_and_preserves_original():
    item = CollectedItem(
        source_type="RSS",
        source="  Some Feed  ",
        title="  A   Title  ",
        url="Example.com/story?utm_source=rss",
        summary="<p>hi</p>",
        raw_text="raw",
        score=1.0,
    )

    [normalized] = normalize_items([item])

    assert isinstance(normalized, ProcessedItem)
    assert normalized.source_type == "rss"
    assert normalized.source == "Some Feed"
    assert normalized.title == "A Title"
    assert normalized.url == "https://example.com/story"
    assert normalized.metadata["original_url"] == "Example.com/story?utm_source=rss"
    assert normalized.metadata["original_title"] == "  A   Title  "
    # Fields the later stages fill in start empty.
    assert normalized.categories == []
    assert normalized.entities == {}
    assert normalized.relevance_score == 0.0
