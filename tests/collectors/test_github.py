"""Tests for app.collectors.github."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.collectors.base import CollectedItem
from app.collectors.github import GitHubCollector, fetch_github_trending

_FAKE_TRENDING_HTML = """
<html><body>
<article class="Box-row">
  <h2 class="h3"><a href="/openai/example-repo">openai / example-repo</a></h2>
  <p class="col-9">An example AI repository.</p>
  <a href="/openai/example-repo/stargazers">
    <svg class="octicon-star"></svg>
    1,234
  </a>
</article>
</body></html>
"""


def _make_fake_async_client(html_text: str):
    fake_response = MagicMock()
    fake_response.text = html_text
    fake_response.raise_for_status = MagicMock()

    fake_client = MagicMock()
    fake_client.get = AsyncMock(return_value=fake_response)
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)
    return fake_client


@pytest.mark.asyncio
async def test_fetch_github_trending_parses_repo_and_stars():
    fake_client = _make_fake_async_client(_FAKE_TRENDING_HTML)

    with patch("app.collectors.github.httpx.AsyncClient", return_value=fake_client):
        items = await fetch_github_trending()

    assert len(items) == 1
    item = items[0]
    assert isinstance(item, CollectedItem)
    assert item.source_type == "github"
    assert item.source == "GitHub Trending"
    assert "openai/example-repo" in item.url
    assert item.score == 1234.0
    assert item.metadata["repo_name"] == "openai/example-repo"
    assert item.metadata["stars"] == 1234.0


@pytest.mark.asyncio
async def test_fetch_github_trending_handles_http_error_gracefully():
    fake_client = MagicMock()
    fake_client.get = AsyncMock(side_effect=RuntimeError("connection failed"))
    fake_client.__aenter__ = AsyncMock(return_value=fake_client)
    fake_client.__aexit__ = AsyncMock(return_value=False)

    with patch("app.collectors.github.httpx.AsyncClient", return_value=fake_client):
        items = await fetch_github_trending()

    assert items == []


@pytest.mark.asyncio
async def test_fetch_github_trending_no_repos_found():
    fake_client = _make_fake_async_client("<html><body>no repos here</body></html>")

    with patch("app.collectors.github.httpx.AsyncClient", return_value=fake_client):
        items = await fetch_github_trending()

    assert items == []


@pytest.mark.asyncio
async def test_github_collector_wraps_fetch_github_trending():
    fake_items = [CollectedItem(source_type="github", source="s", title="t", url="u")]

    with patch("app.collectors.github.fetch_github_trending", return_value=fake_items):
        result = await GitHubCollector().collect()

    assert result == fake_items
