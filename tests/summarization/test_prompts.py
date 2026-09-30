"""Tests for app.summarization.prompts."""

from __future__ import annotations

from datetime import datetime, timezone

from app.processing.normalization import ProcessedItem
from app.summarization.prompts import SYSTEM_PROMPT, build_user_prompt


def _item(**overrides) -> ProcessedItem:
    defaults = dict(
        source_type="rss",
        source="TechCrunch",
        title="OpenAI releases GPT-4o",
        url="https://example.com/story",
        summary="OpenAI announced GPT-4o today.",
        raw_text="It has multimodal capabilities.",
        score=10.0,
        primary_category="LLMs",
        published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    defaults.update(overrides)
    return ProcessedItem(**defaults)


def test_system_prompt_forbids_outside_knowledge_and_requires_json():
    assert "do not invent" in SYSTEM_PROMPT.lower()
    assert "json" in SYSTEM_PROMPT.lower()
    assert '"headline"' in SYSTEM_PROMPT
    assert '"key_points"' in SYSTEM_PROMPT


def test_build_user_prompt_includes_item_content_and_metadata():
    item = _item()
    prompt = build_user_prompt(item)

    assert "OpenAI releases GPT-4o" in prompt
    assert "TechCrunch" in prompt
    assert "OpenAI announced GPT-4o today." in prompt
    assert "multimodal capabilities" in prompt
    assert "LLMs" in prompt
    assert "2026-01-01" in prompt


def test_build_user_prompt_handles_missing_content():
    item = _item(summary="", raw_text="")
    prompt = build_user_prompt(item)
    assert "no additional content" in prompt.lower()


def test_build_user_prompt_handles_unknown_published_date():
    item = _item(published_at=None)
    prompt = build_user_prompt(item)
    assert "unknown" in prompt.lower()


def test_build_user_prompt_truncates_long_content():
    long_text = "word " * 2000  # well over MAX_CONTENT_CHARS
    item = _item(summary=long_text, raw_text="")
    prompt = build_user_prompt(item, max_content_chars=100)
    assert "[content truncated]" in prompt
