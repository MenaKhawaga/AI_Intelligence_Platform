from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, func

from app.api.dependencies import admin_user, db_session
from app.models.user import User
from app.models.article import Article
from app.models.topic import Topic
from app.models.agent_activity import AgentActivity
from app.models.summary import Summary
from app.models.source import Source
from app.database.repositories import list_sources

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def get_users(
    user=Depends(admin_user),
    session=Depends(db_session),
):
    users = session.execute(
        select(User).order_by(User.id)
    ).scalars().all()

    return [
        {
            "id": user.id,
            "email": user.email,
            "active": user.is_active,
            "is_admin": user.is_admin,
            "created_at": user.created_at,
        }
        for user in users
    ]


@router.get("/stats")
def get_stats(
    user=Depends(admin_user),
    session=Depends(db_session),
):
    return {
        "total_users": session.scalar(
            select(func.count()).select_from(User)
        ),
        "total_articles": session.scalar(
            select(func.count()).select_from(Article)
        ),
        "total_topics": session.scalar(
            select(func.count()).select_from(Topic)
        ),
        "total_agent_activities": session.scalar(
            select(func.count()).select_from(AgentActivity)
        ),
    }


@router.get("/agent-activity")
def get_agent_activity(
    user=Depends(admin_user),
    session=Depends(db_session),
):
    activities = session.execute(
        select(AgentActivity)
        .order_by(AgentActivity.created_at.desc())
        .limit(100)
    ).scalars().all()

    return [
        {
            "id": activity.id,
            "user_id": activity.user_id,
            "query": activity.query,
            "tools_used": activity.tools_used,
            "success": activity.success,
            "created_at": activity.created_at,
        }
        for activity in activities
    ]

@router.get("/summaries")
def get_summaries(
    user=Depends(admin_user),
    session=Depends(db_session),
):
    summaries = session.execute(
        select(Summary)
        .order_by(Summary.generated_at.desc())
        .limit(100)
    ).scalars().all()

    return [
        {
            "id": summary.id,
            "article_id": summary.article_id,
            "headline": summary.headline,
            "summary_text": summary.summary_text,
            "why_it_matters": summary.why_it_matters,
            "key_points": summary.key_points,
            "generated_at": summary.generated_at,
        }
        for summary in summaries
    ]

@router.get("/sources")
def get_sources(
    user=Depends(admin_user),
    session=Depends(db_session),
):
    sources = list_sources(session)

    return [
        {
            "id": source.id,
            "name": source.name,
            "source_type": source.source_type,
            "url": source.url,
            "is_active": source.is_active,
            "created_at": source.created_at,
        }
        for source in sources
    ]