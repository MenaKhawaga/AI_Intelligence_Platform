from __future__ import annotations
from fastapi import APIRouter, Depends
from app.api.dependencies import current_user, db_session
from app.core.config import settings
from app.database.repositories import list_topics
from app.scheduler.run_manager import run_manager

router = APIRouter(prefix="/trends", tags=["trends"])


@router.get("")
def trends(user=Depends(current_user), session=Depends(db_session)):
    # ``description`` already carries the explainable score (see
    # app/trends/analyzer.py: "... trend strength=NN/100.") since Topic
    # has no dedicated score column; article_count comes straight from the
    # existing article<->topic relationship, no extra query needed.
    #
    # Sorted by ``last_seen_at`` (most recently active topic first) rather
    # than the repository's default alphabetical order, so the Trends page
    # reads like a news feed -- freshest stories on top -- and each topic
    # carries its most recent articles so the page can show actual
    # headlines, not just a topic name.
    topics = sorted(
        list_topics(session),
        key=lambda t: t.last_seen_at or t.first_seen_at or t.created_at,
        reverse=True,
    )
    return [
        {
            "name": t.name,
            "description": t.description,
            "article_count": len(t.articles),
            "first_seen_at": t.first_seen_at,
            "last_seen_at": t.last_seen_at,
            "articles": [
                {
                    "title": a.title,
                    "url": a.url,
                    "source": a.source,
                    "published_at": a.published_at,
                }
                for a in sorted(
                    t.articles,
                    key=lambda a: a.published_at or a.collected_at,
                    reverse=True,
                )[:5]
            ],
        }
        for t in topics
    ]


@router.get("/status")
def trends_status(user=Depends(current_user)):
    """Background-collector status: whether the hourly scheduler is on,
    how often it runs, and the outcome of its most recent run -- so the
    frontend can show "last updated" / "next refresh" on the Trends page."""

    return {
        "scheduler_enabled": settings.SCHEDULER_ENABLED,
        "collection_interval_minutes": settings.COLLECTION_INTERVAL_MINUTES,
        **run_manager.snapshot(),
    }
