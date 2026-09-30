"""Tests for app.processing.ranking."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.processing.normalization import ProcessedItem
from app.processing.ranking import (
    engagement_score,
    rank_items,
    recency_score,
    score_item,
    source_quality_score,
)


def _item(**overrides) -> ProcessedItem:
    defaults = dict(
        source_type="rss",
        source="Some Feed",
        title="A title",
        url="https://example.com/a",
        summary="",
        raw_text="",
        score=0.0,
    )
    defaults.update(overrides)
    return ProcessedItem(**defaults)


def test_source_quality_score_known_and_unknown_source():
    assert source_quality_score(_item(source_type="arxiv")) == 1.0
    assert source_quality_score(_item(source_type="totally_unknown")) < 1.0


def test_engagement_score_neutral_when_no_native_score():
    item = _item(source_type="arxiv", score=0.0)
    assert engagement_score(item) == 0.5


def test_engagement_score_increases_with_native_score():
    low = engagement_score(_item(source_type="hackernews", score=10))
    high = engagement_score(_item(source_type="hackernews", score=400))
    assert 0.0 < low < high <= 1.0


def test_engagement_score_capped_at_one():
    item = _item(source_type="hackernews", score=1_000_000)
    assert engagement_score(item) <= 1.0


def test_recency_score_recent_higher_than_old():
    now = datetime.now(timezone.utc)
    fresh = _item(published_at=now - timedelta(hours=1))
    old = _item(published_at=now - timedelta(days=30))
    assert recency_score(fresh, now=now) > recency_score(old, now=now)


def test_recency_score_neutral_when_unknown():
    item = _item()
    item.published_at = None
    item.collected_at = None
    assert recency_score(item) == 0.5


def test_score_item_sets_breakdown_and_total_in_range():
    item = _item(
        source_type="hackernews",
        score=200,
        published_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    item.categories = ["LLMs"]
    item.primary_category = "LLMs"
    item.entities = {"companies": ["OpenAI"]}

    score_item(item)

    assert 0.0 <= item.relevance_score <= 100.0
    assert "source_quality_raw" in item.score_breakdown
    assert "engagement_weighted" in item.score_breakdown


def test_rank_items_sorts_descending():
    now = datetime.now(timezone.utc)
    low = _item(url="https://example.com/low", source_type="reddit", score=1, published_at=now - timedelta(days=10))
    high = _item(url="https://example.com/high", source_type="arxiv", score=0, published_at=now)
    high.categories = ["AI Research"]
    high.primary_category = "AI Research"

    ranked = rank_items([low, high], now=now)

    assert ranked[0].relevance_score >= ranked[1].relevance_score
