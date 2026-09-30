"""Phase 7 — persistence bridge for detected trends."""

from __future__ import annotations

from typing import Sequence

from app.database.repositories import get_article_by_url, get_or_create_topic, link_article_to_topic
from app.database.session import get_session
from app.processing.normalization import ProcessedItem
from app.summarization.structured_output import ArticleSummary
from app.trends.analyzer import analyze_trends


def persist_trends(
    items: Sequence[ProcessedItem],
    summaries: Sequence[ArticleSummary],
    *,
    session_scope=get_session,
) -> int:
    """Detect trends and persist topic memberships for stored articles.

    The pipeline already persists articles before this hook runs, so this
    function only updates the Phase 5 topic tables; it never changes
    article content or summary data.
    """

    del summaries  # Reserved by the common PipelineHook contract.
    trends = analyze_trends(items)
    linked = 0

    with session_scope() as session:
        for trend in trends:
            topic = get_or_create_topic(
                session,
                trend.name,
                description=trend.description,
            )
            for item in trend.items:
                article = get_article_by_url(session, item.url)
                if article is None:
                    continue
                before = len(article.topics)
                link_article_to_topic(session, article, topic)
                if len(article.topics) > before:
                    linked += 1

            topic.first_seen_at = trend.first_seen_at
            topic.last_seen_at = trend.last_seen_at
            session.flush()

    return linked
