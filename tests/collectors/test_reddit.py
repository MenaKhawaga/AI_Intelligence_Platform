"""Tests for app.collectors.reddit."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.collectors.base import CollectedItem
from app.collectors.reddit import AI_SUBREDDITS, RedditCollector, fetch_reddit


def _fake_settings(client_id=None, client_secret=None):
    return SimpleNamespace(
        reddit_client_id=client_id,
        reddit_client_secret=client_secret,
        reddit_user_agent="test-agent/1.0",
    )


def _fake_post(title, ups, num_comments, url=None, permalink="/r/x/comments/1", selftext=""):
    return SimpleNamespace(
        title=title,
        selftext=selftext,
        ups=ups,
        num_comments=num_comments,
        url=url or f"https://reddit.com{permalink}",
        permalink=permalink,
        created_utc=datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp(),
    )


@pytest.mark.asyncio
async def test_fetch_reddit_skips_when_credentials_missing():
    with patch("app.collectors.reddit.settings", return_value=_fake_settings()):
        with patch("app.collectors.reddit.praw.Reddit") as mock_reddit_cls:
            items = await fetch_reddit()

    assert items == []
    mock_reddit_cls.assert_not_called()


@pytest.mark.asyncio
async def test_fetch_reddit_returns_collected_items_when_configured():
    fake_settings = _fake_settings(client_id="id", client_secret="secret")
    fake_post = _fake_post("A great AI post", ups=42, num_comments=7)

    fake_subreddit = MagicMock()
    fake_subreddit.top = MagicMock(return_value=[fake_post])

    fake_reddit_instance = MagicMock()
    fake_reddit_instance.subreddit = MagicMock(return_value=fake_subreddit)

    with patch("app.collectors.reddit.settings", return_value=fake_settings):
        with patch(
            "app.collectors.reddit.praw.Reddit", return_value=fake_reddit_instance
        ) as mock_reddit_cls:
            with patch("app.collectors.reddit.AI_SUBREDDITS", ["MachineLearning"]):
                items = await fetch_reddit()

    mock_reddit_cls.assert_called_once_with(
        client_id="id", client_secret="secret", user_agent="test-agent/1.0"
    )
    assert len(items) == 1
    item = items[0]
    assert isinstance(item, CollectedItem)
    assert item.source_type == "reddit"
    assert item.source == "Reddit (r/MachineLearning)"
    assert item.title == "A great AI post"
    assert item.score == 42.0
    assert item.metadata == {
        "subreddit": "MachineLearning",
        "ups": 42,
        "num_comments": 7,
    }


@pytest.mark.asyncio
async def test_fetch_reddit_continues_after_one_subreddit_fails():
    fake_settings = _fake_settings(client_id="id", client_secret="secret")
    fake_post = _fake_post("Still works", ups=10, num_comments=2)

    def _subreddit_side_effect(name):
        if name == "Broken":
            raise RuntimeError("subreddit unavailable")
        fake_subreddit = MagicMock()
        fake_subreddit.top = MagicMock(return_value=[fake_post])
        return fake_subreddit

    fake_reddit_instance = MagicMock()
    fake_reddit_instance.subreddit = MagicMock(side_effect=_subreddit_side_effect)

    with patch("app.collectors.reddit.settings", return_value=fake_settings):
        with patch("app.collectors.reddit.praw.Reddit", return_value=fake_reddit_instance):
            with patch(
                "app.collectors.reddit.AI_SUBREDDITS", ["Broken", "MachineLearning"]
            ):
                items = await fetch_reddit()

    assert len(items) == 1
    assert items[0].title == "Still works"


def test_ai_subreddits_not_empty():
    assert len(AI_SUBREDDITS) > 0


@pytest.mark.asyncio
async def test_reddit_collector_wraps_fetch_reddit():
    fake_items = [CollectedItem(source_type="reddit", source="s", title="t", url="u")]

    with patch("app.collectors.reddit.fetch_reddit", return_value=fake_items):
        result = await RedditCollector().collect()

    assert result == fake_items
