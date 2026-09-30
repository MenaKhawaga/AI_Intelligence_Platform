"""Tests for app.summarization.structured_output."""

from __future__ import annotations

import pytest

from app.processing.normalization import ProcessedItem
from app.summarization.structured_output import (
    ArticleSummary,
    LLMSummaryFields,
    SummaryParseError,
    build_article_summary,
    parse_llm_json,
)


def _item(**overrides) -> ProcessedItem:
    defaults = dict(
        source_type="rss",
        source="TechCrunch",
        title="OpenAI releases GPT-4o",
        url="https://example.com/story",
        summary="OpenAI announced GPT-4o today.",
        raw_text="",
        score=10.0,
        primary_category="LLMs",
        entities={"companies": ["OpenAI"], "models": ["GPT-4o"]},
        relevance_score=87.5,
    )
    defaults.update(overrides)
    return ProcessedItem(**defaults)


VALID_JSON = """{
  "headline": "OpenAI ships GPT-4o",
  "summary": "OpenAI released GPT-4o, a new model.",
  "key_points": ["Released today", "New model called GPT-4o"],
  "why_it_matters": "It expands OpenAI's model lineup."
}"""


def test_parse_llm_json_valid():
    fields = parse_llm_json(VALID_JSON)
    assert isinstance(fields, LLMSummaryFields)
    assert fields.headline == "OpenAI ships GPT-4o"
    assert fields.key_points == ["Released today", "New model called GPT-4o"]


def test_parse_llm_json_strips_markdown_code_fences():
    fenced = f"```json\n{VALID_JSON}\n```"
    fields = parse_llm_json(fenced)
    assert fields.headline == "OpenAI ships GPT-4o"


def test_parse_llm_json_empty_raises():
    with pytest.raises(SummaryParseError):
        parse_llm_json("")
    with pytest.raises(SummaryParseError):
        parse_llm_json("   ")


def test_parse_llm_json_invalid_json_raises():
    with pytest.raises(SummaryParseError):
        parse_llm_json("not json at all")


def test_parse_llm_json_not_an_object_raises():
    with pytest.raises(SummaryParseError):
        parse_llm_json('["just", "a", "list"]')


def test_parse_llm_json_missing_field_raises():
    bad = '{"headline": "x", "summary": "y", "key_points": ["a"]}'  # no why_it_matters
    with pytest.raises(SummaryParseError):
        parse_llm_json(bad)


def test_parse_llm_json_blank_field_raises():
    bad = VALID_JSON.replace('"OpenAI ships GPT-4o"', '""')
    with pytest.raises(SummaryParseError):
        parse_llm_json(bad)


def test_parse_llm_json_empty_key_points_raises():
    bad = '{"headline": "x", "summary": "y", "key_points": [], "why_it_matters": "z"}'
    with pytest.raises(SummaryParseError):
        parse_llm_json(bad)


def test_parse_llm_json_drops_blank_key_points():
    raw = '{"headline": "x", "summary": "y", "key_points": ["a", "  ", ""], "why_it_matters": "z"}'
    fields = parse_llm_json(raw)
    assert fields.key_points == ["a"]


def test_build_article_summary_uses_item_for_deterministic_fields():
    item = _item()
    fields = parse_llm_json(VALID_JSON)

    summary = build_article_summary(item, fields)

    assert isinstance(summary, ArticleSummary)
    # LLM-provided fields pass through.
    assert summary.headline == fields.headline
    assert summary.summary == fields.summary
    assert summary.key_points == fields.key_points
    assert summary.why_it_matters == fields.why_it_matters
    # Deterministic fields come from the item, not the LLM.
    assert summary.category == "LLMs"
    assert summary.entities == {"companies": ["OpenAI"], "models": ["GPT-4o"]}
    assert summary.source_url == "https://example.com/story"
    assert summary.source_title == "OpenAI releases GPT-4o"
    assert summary.source == "TechCrunch"
    assert summary.relevance_score == 87.5


def test_build_article_summary_falls_back_category_when_uncategorized():
    item = _item(primary_category=None)
    fields = parse_llm_json(VALID_JSON)

    summary = build_article_summary(item, fields)

    assert summary.category == "AI/ML"
