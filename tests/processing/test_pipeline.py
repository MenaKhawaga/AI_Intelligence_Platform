"""End-to-end tests for app.processing.process_items (the full pipeline)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.collectors.base import CollectedItem
from app.processing import ProcessedItem, process_items


def test_process_items_end_to_end():
    now = datetime.now(timezone.utc)
    raw_items = [
        CollectedItem(
            source_type="hackernews",
            source="Hacker News (AI)",
            title="  OpenAI releases new   GPT-4o model &amp; API  ",
            url="https://example.com/story?utm_source=hn&ref=x#frag",
            summary="<p>OpenAI announced GPT-4o today. <b>Read more</b></p>",
            raw_text="OpenAI GPT-4o launch details.",
            score=250,
            published_at=now - timedelta(hours=2),
        ),
        # Same story, different source -- should be merged by deduplication.
        CollectedItem(
            source_type="rss",
            source="TechCrunch",
            title="OpenAI releases new GPT-4o model and API",
            url="https://example.com/story/",
            summary="OpenAI announced GPT-4o today with big improvements.",
            score=0,
            published_at=now - timedelta(hours=3),
        ),
        # Off-topic -- should be dropped by filtering.
        CollectedItem(
            source_type="reddit",
            source="r/pics",
            title="My cat sleeping in a box",
            url="https://example.com/cat",
            summary="Just a cute cat picture, nothing else.",
            score=500,
        ),
        # Malformed -- should be dropped by cleaning.
        CollectedItem(
            source_type="github",
            source="GitHub",
            title="",
            url="not-a-url",
            score=0,
        ),
    ]

    result = process_items(raw_items)

    # Off-topic and malformed items are gone; the duplicate pair merged into one.
    assert len(result) == 1
    item = result[0]
    assert isinstance(item, ProcessedItem)
    assert item.duplicate_count == 1
    assert "TechCrunch" in item.duplicate_sources
    assert item.primary_category == "LLMs"
    assert "OpenAI" in item.entities.get("companies", [])
    assert "GPT-4o" in item.entities.get("models", [])
    assert 0.0 <= item.relevance_score <= 100.0


def test_process_items_empty_input():
    assert process_items([]) == []


def test_process_items_is_sorted_by_relevance_descending():
    now = datetime.now(timezone.utc)
    raw_items = [
        CollectedItem(
            source_type="reddit",
            source="r/MachineLearning",
            title="A minor AI update nobody cares about",
            url="https://example.com/minor",
            summary="A small AI tweak.",
            score=1,
            published_at=now - timedelta(days=20),
        ),
        CollectedItem(
            source_type="arxiv",
            source="arXiv",
            title="Breakthrough new LLM agent architecture beats prior benchmarks",
            url="https://arxiv.org/abs/9999.9999",
            summary="A new transformer-based AI agent paper with strong results.",
            score=0,
            published_at=now,
        ),
    ]

    result = process_items(raw_items)

    assert len(result) == 2
    assert result[0].relevance_score >= result[1].relevance_score
    assert result[0].url == "https://arxiv.org/abs/9999.9999"
