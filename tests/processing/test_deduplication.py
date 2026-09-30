"""Tests for app.processing.deduplication."""

from __future__ import annotations

from app.processing.deduplication import deduplicate_items, title_similarity
from app.processing.normalization import ProcessedItem


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


def test_title_similarity_identical_ignoring_case_and_punctuation():
    assert title_similarity("GPT-4o is here!", "gpt 4o is here") > 0.9


def test_title_similarity_unrelated_titles_low():
    assert title_similarity("OpenAI releases GPT-4o", "Cats are great pets") < 0.5


def test_deduplicate_exact_url_match_merges_and_keeps_higher_score():
    a = _item(source="Feed A", url="https://example.com/story", score=10)
    b = _item(source="Feed B", url="https://example.com/story", score=50)

    result = deduplicate_items([a, b])

    assert len(result) == 1
    kept = result[0]
    assert kept.score == 50
    assert kept.duplicate_count == 1
    assert "Feed A" in kept.duplicate_sources


def test_deduplicate_near_duplicate_titles_merge():
    a = _item(
        source="Hacker News",
        url="https://example.com/a",
        title="OpenAI releases new GPT-4o model and API",
        score=100,
    )
    b = _item(
        source="TechCrunch",
        url="https://techcrunch.com/b",
        title="OpenAI releases new GPT-4o model & API",
        score=20,
    )

    result = deduplicate_items([a, b])

    assert len(result) == 1
    assert result[0].score == 100
    assert "TechCrunch" in result[0].duplicate_sources


def test_deduplicate_distinct_items_all_kept():
    a = _item(url="https://example.com/a", title="OpenAI releases GPT-4o")
    b = _item(url="https://example.com/b", title="A robot learns to walk")

    result = deduplicate_items([a, b])

    assert len(result) == 2


def test_deduplicate_empty_list():
    assert deduplicate_items([]) == []
