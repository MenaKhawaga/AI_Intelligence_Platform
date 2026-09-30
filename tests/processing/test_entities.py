"""Tests for app.processing.entities."""

from __future__ import annotations

from app.processing.entities import extract_entities, extract_entities_from_text
from app.processing.normalization import ProcessedItem


def _item(**overrides) -> ProcessedItem:
    defaults = dict(
        source_type="rss",
        source="Some Feed",
        title="",
        url="https://example.com/a",
        summary="",
        raw_text="",
        score=0.0,
    )
    defaults.update(overrides)
    return ProcessedItem(**defaults)


def test_extract_entities_finds_company_and_model():
    text = "OpenAI announced GPT-4o today, a big step for the company."
    found = extract_entities_from_text(text)
    assert found["companies"] == ["OpenAI"]
    assert found["models"] == ["GPT-4o"]


def test_extract_entities_finds_people_and_organizations():
    text = "Sam Altman spoke at MIT about the future of AI research."
    found = extract_entities_from_text(text)
    assert found["people"] == ["Sam Altman"]
    assert found["organizations"] == ["MIT"]


def test_extract_entities_finds_technologies():
    text = "The new model uses LoRA fine-tuning and a mixture of experts architecture."
    found = extract_entities_from_text(text)
    assert "LoRA" in found["technologies"]
    assert "mixture of experts" in found["technologies"]


def test_extract_entities_word_boundary_avoids_false_positive():
    # "AI2" (an organization) should not match inside an unrelated word.
    text = "The user id was SAI27X, nothing about the org here."
    found = extract_entities_from_text(text)
    assert "organizations" not in found


def test_extract_entities_no_matches_returns_empty_dict():
    text = "A totally unrelated sentence about gardening."
    assert extract_entities_from_text(text) == {}


def test_extract_entities_item_sets_entities_field():
    item = _item(title="OpenAI releases GPT-4o", summary="Sam Altman announced it at MIT.")
    [processed] = extract_entities([item])
    assert processed.entities["companies"] == ["OpenAI"]
    assert processed.entities["people"] == ["Sam Altman"]
    assert processed.entities["organizations"] == ["MIT"]
