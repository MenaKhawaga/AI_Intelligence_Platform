"""Tests for app.collectors.arxiv."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.base import CollectedItem
from app.collectors.arxiv import ArxivCollector, fetch_arxiv_papers

_FAKE_ATOM_XML = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>https://arxiv.org/abs/2401.00001v1</id>
    <title>A Great Paper On AI</title>
    <summary>This paper studies something interesting about AI.</summary>
    <published>2024-01-01T00:00:00Z</published>
    <author><name>Jane Doe</name></author>
    <author><name>John Smith</name></author>
  </entry>
</feed>
"""


def _make_fake_client(xml_text: str):
    fake_response = MagicMock()
    fake_response.text = xml_text
    fake_response.raise_for_status = MagicMock()

    fake_client = MagicMock()
    fake_client.get = AsyncMock(return_value=fake_response)
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)
    return fake_client


@pytest.mark.asyncio
async def test_fetch_arxiv_papers_parses_entries():
    fake_client = _make_fake_client(_FAKE_ATOM_XML)

    with patch("app.collectors.arxiv.httpx.AsyncClient", return_value=fake_client):
        with patch("app.collectors.arxiv.asyncio.sleep", AsyncMock()):
            with patch(
                "app.collectors.arxiv.ARXIV_CATEGORIES", ["cat:cs.AI"]
            ):
                items = await fetch_arxiv_papers()

    assert len(items) == 1
    item = items[0]
    assert isinstance(item, CollectedItem)
    assert item.source_type == "arxiv"
    assert item.source == "ArXiv"
    assert "A Great Paper On AI" in item.title
    assert item.url == "https://arxiv.org/abs/2401.00001v1"
    assert item.published_at is not None
    assert item.metadata["arxiv_id"] == "2401.00001v1"
    assert item.metadata["authors"] == ["Jane Doe", "John Smith"]


@pytest.mark.asyncio
async def test_fetch_arxiv_papers_handles_rate_limit():
    import httpx

    fake_response = MagicMock(status_code=429)
    error = httpx.HTTPStatusError("rate limited", request=MagicMock(), response=fake_response)

    fake_client = MagicMock()
    fake_client.get = AsyncMock(side_effect=error)
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.collectors.arxiv.httpx.AsyncClient", return_value=fake_client):
        with patch("app.collectors.arxiv.asyncio.sleep", AsyncMock()):
            items = await fetch_arxiv_papers()

    assert items == []


@pytest.mark.asyncio
async def test_arxiv_collector_wraps_fetch_arxiv_papers():
    fake_items = [CollectedItem(source_type="arxiv", source="s", title="t", url="u")]

    with patch("app.collectors.arxiv.fetch_arxiv_papers", return_value=fake_items):
        result = await ArxivCollector().collect()

    assert result == fake_items
