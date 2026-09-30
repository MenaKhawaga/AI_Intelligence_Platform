"""Tests for app.processing.classification."""

from __future__ import annotations

from app.processing.classification import DEFAULT_CATEGORY_KEYWORDS, classify_item, classify_items
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


def test_classify_item_llm_category():
    item = _item(title="New LLM chatbot beats GPT-4 on benchmarks")
    classify_item(item)
    assert item.primary_category == "LLMs"
    assert "LLMs" in item.categories


def test_classify_item_computer_vision_category():
    item = _item(title="New object detection model improves image recognition")
    classify_item(item)
    assert item.primary_category == "Computer Vision"


def test_classify_item_robotics_category():
    item = _item(title="Humanoid robot learns to walk using reinforcement learning")
    classify_item(item)
    assert "Robotics" in item.categories


def test_classify_item_open_source_category():
    item = _item(title="New open-source AI model released on GitHub with Apache license")
    classify_item(item)
    assert "Open Source AI" in item.categories


def test_classify_item_falls_back_to_generic_category():
    item = _item(title="Artificial intelligence transforms an unrelated industry")
    classify_item(item)
    # Matches only the generic AI/ML bucket, nothing more specific.
    assert item.primary_category == "AI/ML"


def test_classify_item_multiple_categories_ranked_by_match_count():
    item = _item(
        title="Open-source LLM agent framework",
        summary="An agentic, open source LLM tool for developers, released on GitHub with an MIT license",
    )
    classify_item(item)
    assert len(item.categories) > 1
    assert item.primary_category == item.categories[0]


def test_classify_items_batch():
    items = [
        _item(title="New LLM beats GPT-4 benchmarks"),
        _item(title="Robot arm uses reinforcement learning to grasp objects"),
    ]
    classify_items(items, DEFAULT_CATEGORY_KEYWORDS)
    assert items[0].primary_category == "LLMs"
    assert "Robotics" in items[1].categories
