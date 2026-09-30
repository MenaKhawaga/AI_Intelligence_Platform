"""Tests for app.collectors.hackernews."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.base import CollectedItem
from app.collectors.hackernews import HackerNewsCollector, fetch_hackernews


def _make_fake_client(hits_by_query):
    """hits_by_query: dict mapping the `query` param to a list of hit dicts."""

    async def _get(url, params=None, **kwargs):
        query = (params or {}).get("query")
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json = MagicMock(return_value={"hits": hits_by_query.get(query, [])})
        return response

    fake_client = MagicMock()
    fake_client.get = AsyncMock(side_effect=_get)
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)
    return fake_client


@pytest.mark.asyncio
async def test_fetch_hackernews_returns_items_with_urls_only():
    hits_by_query = {
        "AI": [
            {"title": "AI story", "url": "https://example.com/ai", "points": 120, "num_comments": 30},
            {"title": "No url story", "points": 90, "num_comments": 5},  # no url -> skipped
        ],
        "machine learning": [],
        "LLM": [],
    }
    fake_client = _make_fake_client(hits_by_query)

    with patch("app.collectors.hackernews.httpx.AsyncClient", return_value=fake_client):
        items = await fetch_hackernews()

    assert len(items) == 1
    item = items[0]
    assert isinstance(item, CollectedItem)
    assert item.source_type == "hackernews"
    assert item.title == "AI story"
    assert item.url == "https://example.com/ai"
    assert item.score == 120.0
    assert item.metadata == {"keyword": "AI", "points": 120, "num_comments": 30}


@pytest.mark.asyncio
async def test_fetch_hackernews_handles_request_error_per_keyword():
    import httpx

    async def _get(url, params=None, **kwargs):
        if (params or {}).get("query") == "AI":
            raise httpx.RequestError("boom")
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json = MagicMock(return_value={"hits": []})
        return response

    fake_client = MagicMock()
    fake_client.get = AsyncMock(side_effect=_get)
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.collectors.hackernews.httpx.AsyncClient", return_value=fake_client):
        items = await fetch_hackernews()

    assert items == []


@pytest.mark.asyncio
async def test_hackernews_collector_wraps_fetch_hackernews():
    fake_items = [CollectedItem(source_type="hackernews", source="s", title="t", url="u")]

    with patch("app.collectors.hackernews.fetch_hackernews", return_value=fake_items):
        result = await HackerNewsCollector().collect()

    assert result == fake_items
