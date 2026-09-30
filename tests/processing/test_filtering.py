"""Tests for app.processing.filtering."""

from __future__ import annotations

from app.processing.filtering import FilterConfig, filter_items, passes_filters
from app.processing.normalization import ProcessedItem


def _item(**overrides) -> ProcessedItem:
    defaults = dict(
        source_type="rss",
        source="Some Feed",
        title="OpenAI releases a new model",
        url="https://example.com/a",
        summary="",
        raw_text="",
        score=0.0,
    )
    defaults.update(overrides)
    return ProcessedItem(**defaults)


def test_passes_filters_keeps_ai_related_item():
    item = _item(title="New transformer architecture beats GPT-4 benchmarks")
    assert passes_filters(item) is True


def test_passes_filters_drops_non_ai_item():
    item = _item(title="Local bakery wins pastry award", summary="Delicious croissants")
    assert passes_filters(item) is False


def test_passes_filters_drops_short_title():
    item = _item(title="AI news")
    assert passes_filters(item) is False


def test_passes_filters_drops_blocked_keyword():
    item = _item(title="Sponsored: buy this AI gadget now", summary="advertisement")
    assert passes_filters(item) is False


def test_passes_filters_respects_min_score():
    config = FilterConfig(min_score=10.0)
    item = _item(title="OpenAI releases a strong new AI model", score=5.0)
    assert passes_filters(item, config) is False


def test_passes_filters_respects_allowed_source_types():
    config = FilterConfig(allowed_source_types={"arxiv"})
    item = _item(title="OpenAI releases a strong new AI model", source_type="rss")
    assert passes_filters(item, config) is False


def test_filter_items_returns_only_passing_items():
    ai_item = _item(title="OpenAI releases a strong new AI model")
    off_topic = _item(title="Local bakery wins pastry award", summary="Croissants")

    result = filter_items([ai_item, off_topic])

    assert result == [ai_item]


def test_filter_items_can_disable_ai_keyword_requirement():
    config = FilterConfig(require_ai_keyword=False)
    off_topic = _item(title="Local bakery wins pastry award")

    result = filter_items([off_topic], config)

    assert result == [off_topic]
