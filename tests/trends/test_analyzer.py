from datetime import datetime, timedelta, timezone

from app.collectors.base import CollectedItem
from app.processing.normalization import ProcessedItem
from app.trends.analyzer import analyze_trends


NOW = datetime(2026, 1, 8, 12, tzinfo=timezone.utc)


def make_item(title, source, hours_ago):
    return ProcessedItem(
        **CollectedItem(
            source_type=source,
            source=source,
            title=title,
            url=f"https://example.com/{source}/{hours_ago}/{title}",
            published_at=NOW - timedelta(hours=hours_ago),
        ).model_dump(),
        categories=["LLMs"],
        primary_category="LLMs",
        entities={"companies": ["OpenAI"]},
    )


def test_analyzer_returns_ranked_trends_with_evidence():
    items = [
        make_item("OpenAI model release", "rss", 2),
        make_item("OpenAI model update", "github", 4),
        make_item("OpenAI model research", "arxiv", 48),
    ]
    trends = analyze_trends(items, now=NOW, similarity_threshold=0.20)

    assert trends
    trend = trends[0]
    assert trend.name == "OpenAI"
    assert trend.item_count == 3
    assert trend.source_count == 3
    assert trend.score.strength >= 0
    assert "related item" in trend.description
