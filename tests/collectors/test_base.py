"""Tests for app.collectors.base: CollectedItem, async_retry, BaseCollector."""

from __future__ import annotations

import pytest

from app.collectors.base import BaseCollector, CollectedItem, async_retry


def test_collected_item_defaults():
    """Only the required fields need to be supplied; the rest default sanely."""

    item = CollectedItem(
        source_type="rss",
        source="Some Feed",
        title="A title",
        url="https://example.com/a",
    )

    assert item.summary == ""
    assert item.raw_text == ""
    assert item.score == 0.0
    assert item.published_at is None
    assert item.metadata == {}
    assert item.collected_at is not None


def test_collected_item_carries_metadata():
    item = CollectedItem(
        source_type="arxiv",
        source="ArXiv",
        title="A paper",
        url="https://arxiv.org/abs/1234.5678",
        metadata={"arxiv_id": "1234.5678", "authors": ["A. Author"]},
    )

    assert item.metadata["arxiv_id"] == "1234.5678"
    assert item.metadata["authors"] == ["A. Author"]


@pytest.mark.asyncio
async def test_async_retry_succeeds_first_try():
    calls = []

    @async_retry(max_retries=3, backoff_factor=1, initial_delay=0)
    async def flaky():
        calls.append(1)
        return "ok"

    result = await flaky()

    assert result == "ok"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_async_retry_retries_then_succeeds():
    calls = []

    @async_retry(max_retries=3, backoff_factor=1, initial_delay=0)
    async def flaky():
        calls.append(1)
        if len(calls) < 2:
            raise ValueError("transient failure")
        return "ok"

    result = await flaky()

    assert result == "ok"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_async_retry_raises_after_max_attempts():
    calls = []

    @async_retry(max_retries=2, backoff_factor=1, initial_delay=0)
    async def always_fails():
        calls.append(1)
        raise ValueError("permanent failure")

    with pytest.raises(ValueError):
        await always_fails()

    assert len(calls) == 2


class _DummyCollector(BaseCollector):
    source_type = "dummy"

    def __init__(self, items=None, should_raise=False):
        self._items = items or []
        self._should_raise = should_raise

    async def _fetch(self):
        if self._should_raise:
            raise RuntimeError("source is down")
        return self._items


@pytest.mark.asyncio
async def test_base_collector_returns_items_on_success():
    expected = [
        CollectedItem(source_type="dummy", source="Dummy", title="t", url="u")
    ]
    collector = _DummyCollector(items=expected)

    result = await collector.collect()

    assert result == expected


@pytest.mark.asyncio
async def test_base_collector_never_raises_returns_empty_list_on_failure():
    collector = _DummyCollector(should_raise=True)

    result = await collector.collect()

    assert result == []


def test_base_collector_is_abstract():
    with pytest.raises(TypeError):
        BaseCollector()  # type: ignore[abstract]
