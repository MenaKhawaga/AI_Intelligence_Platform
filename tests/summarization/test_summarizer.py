"""Tests for app.summarization.summarizer.

All tests use ``FakeLLMService`` below instead of ``OpenAILLMService`` --
no real network call or API key is ever involved.
"""

from __future__ import annotations

from typing import List, Optional

import pytest

from app.processing.normalization import ProcessedItem
from app.services.llm_service import LLMService, LLMServiceError
from app.summarization.summarizer import summarize_item, summarize_items

VALID_JSON = """{
  "headline": "OpenAI ships GPT-4o",
  "summary": "OpenAI released GPT-4o, a new multimodal model.",
  "key_points": ["Released today", "Multimodal capabilities"],
  "why_it_matters": "It expands OpenAI's model lineup."
}"""


class FakeLLMService(LLMService):
    """Scripted fake: returns queued responses/exceptions in order."""

    def __init__(self, responses: List):
        self._responses = list(responses)
        self.calls = 0

    async def complete(self, *, system: str, user: str, temperature: float = 0.2, max_tokens: int = 700) -> str:
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


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
        entities={"companies": ["OpenAI"]},
    )
    defaults.update(overrides)
    return ProcessedItem(**defaults)


@pytest.mark.asyncio
async def test_summarize_item_success():
    item = _item()
    fake = FakeLLMService([VALID_JSON])

    result = await summarize_item(item, fake)

    assert result.ok is True
    assert result.error is None
    assert result.item is item
    assert result.summary.headline == "OpenAI ships GPT-4o"
    assert result.summary.source_url == item.url
    assert result.summary.category == "LLMs"


@pytest.mark.asyncio
async def test_summarize_item_llm_failure_is_captured_not_raised():
    item = _item()
    # async_retry(max_retries=2) means it will try twice before giving up.
    fake = FakeLLMService([LLMServiceError("boom"), LLMServiceError("boom again")])

    result = await summarize_item(item, fake)

    assert result.ok is False
    assert result.summary is None
    assert "boom" in result.error
    assert result.item is item
    assert fake.calls == 2


@pytest.mark.asyncio
async def test_summarize_item_retries_transient_failure_then_succeeds():
    item = _item()
    fake = FakeLLMService([LLMServiceError("transient"), VALID_JSON])

    result = await summarize_item(item, fake)

    assert result.ok is True
    assert fake.calls == 2


@pytest.mark.asyncio
async def test_summarize_item_malformed_json_is_captured_not_raised():
    item = _item()
    fake = FakeLLMService(["not valid json"])

    result = await summarize_item(item, fake)

    assert result.ok is False
    assert result.summary is None
    assert result.error is not None
    assert result.item is item


@pytest.mark.asyncio
async def test_summarize_item_preserves_original_item_on_failure():
    item = _item(title="Some very specific original title")
    fake = FakeLLMService([LLMServiceError("down"), LLMServiceError("down")])

    result = await summarize_item(item, fake)

    assert result.item.title == "Some very specific original title"
    assert result.item.url == item.url


@pytest.mark.asyncio
async def test_summarize_items_batch_mixed_results():
    good_item = _item(url="https://example.com/good")
    bad_item = _item(url="https://example.com/bad", title="A bad item")

    fake = FakeLLMService([VALID_JSON, LLMServiceError("x"), LLMServiceError("x")])

    results = await summarize_items([good_item, bad_item], fake)

    assert len(results) == 2
    assert results[0].ok is True
    assert results[1].ok is False
    # Order matches input order.
    assert results[0].item.url == "https://example.com/good"
    assert results[1].item.url == "https://example.com/bad"


@pytest.mark.asyncio
async def test_summarize_items_respects_limit():
    items = [_item(url=f"https://example.com/{i}") for i in range(5)]
    fake = FakeLLMService([VALID_JSON, VALID_JSON])

    results = await summarize_items(items, fake, limit=2)

    assert len(results) == 2
    assert fake.calls == 2


@pytest.mark.asyncio
async def test_summarize_items_empty_list():
    fake = FakeLLMService([])
    results = await summarize_items([], fake)
    assert results == []
