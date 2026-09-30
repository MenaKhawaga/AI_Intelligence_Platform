"""Tests for app.collectors.rss."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.collectors.base import CollectedItem
from app.collectors.rss import RSSCollector, _is_valid_feed, fetch_rss


class _FakeFeedDict(dict):
    """Minimal stand-in for feedparser's dict-like entry/feed objects."""


def _make_fake_parsed_feed(entries, feed_title="RSS Feed", bozo=False, bozo_exception=""):
    return SimpleNamespace(
        bozo=bozo,
        bozo_exception=bozo_exception,
        feed=_FakeFeedDict(title=feed_title),
        entries=[_FakeFeedDict(e) for e in entries],
    )


@pytest.mark.asyncio
async def test_fetch_rss_returns_collected_items():
    fake_feed = _make_fake_parsed_feed(
        entries=[
            {"title": "AI breakthrough", "summary": "Something happened", "link": "https://example.com/1"},
            {"title": "Another AI story", "summary": "More details", "link": "https://example.com/2"},
        ],
        feed_title="Example AI Blog",
    )

    with patch("app.collectors.rss.feedparser.parse", return_value=fake_feed):
        with patch("app.collectors.rss.AI_RSS_FEEDS", ["https://example.com/feed"]):
            items = await fetch_rss()

    assert len(items) == 2
    assert all(isinstance(item, CollectedItem) for item in items)
    assert items[0].source_type == "rss"
    assert items[0].source == "Example AI Blog"
    assert items[0].title == "AI breakthrough"
    assert items[0].url == "https://example.com/1"
    assert items[0].metadata["feed_url"] == "https://example.com/feed"


@pytest.mark.asyncio
async def test_fetch_rss_skips_invalid_feeds():
    fake_feed = _make_fake_parsed_feed(
        entries=[{"title": "x", "summary": "y", "link": "https://example.com/1"}],
        bozo=True,
        bozo_exception="document is not well-formed",
    )

    with patch("app.collectors.rss.feedparser.parse", return_value=fake_feed):
        with patch("app.collectors.rss.AI_RSS_FEEDS", ["https://example.com/broken-feed"]):
            items = await fetch_rss()

    assert items == []


@pytest.mark.asyncio
async def test_fetch_rss_handles_exception_per_feed_and_continues():
    good_feed = _make_fake_parsed_feed(
        entries=[{"title": "ok", "summary": "s", "link": "https://example.com/ok"}],
        feed_title="Good Feed",
    )

    def _parse_side_effect(url):
        if "bad" in url:
            raise ValueError("network error")
        return good_feed

    with patch("app.collectors.rss.feedparser.parse", side_effect=_parse_side_effect):
        with patch(
            "app.collectors.rss.AI_RSS_FEEDS",
            ["https://example.com/bad-feed", "https://example.com/good-feed"],
        ):
            items = await fetch_rss()

    assert len(items) == 1
    assert items[0].title == "ok"


def test_is_valid_feed_flags_known_malformed_reasons():
    feed = SimpleNamespace(bozo=True, bozo_exception="not well-formed (invalid token)")
    assert _is_valid_feed(feed, "https://example.com/feed") is False


def test_is_valid_feed_accepts_clean_feed():
    feed = SimpleNamespace(bozo=False, bozo_exception="")
    assert _is_valid_feed(feed, "https://example.com/feed") is True


@pytest.mark.asyncio
async def test_rss_collector_wraps_fetch_rss():
    fake_items = [CollectedItem(source_type="rss", source="s", title="t", url="u")]

    with patch("app.collectors.rss.fetch_rss", return_value=fake_items):
        result = await RSSCollector().collect()

    assert result == fake_items
