from datetime import datetime, timedelta, timezone

from app.collectors.base import CollectedItem
from app.processing.normalization import ProcessedItem
from app.trends.signals import compute_signals


NOW = datetime(2026, 1, 8, 12, tzinfo=timezone.utc)


def item(title, source, hours_ago):
    return ProcessedItem(
        **CollectedItem(
            source_type=source,
            source=source,
            title=title,
            url=f"https://example.com/{title.replace(' ', '-')}",
            published_at=NOW - timedelta(hours=hours_ago),
        ).model_dump()
    )


def test_signals_capture_recent_activity_and_source_diversity():
    items = [
        item("A", "rss", 2),
        item("B", "github", 4),
        item("C", "arxiv", 48),
        item("D", "rss", 72),
    ]
    signal = compute_signals(items, now=NOW)

    assert signal.volume == 4
    assert signal.recent_volume == 2
    assert signal.baseline_volume == 2
    assert signal.source_diversity == 0.75
    assert signal.velocity > 1.0
