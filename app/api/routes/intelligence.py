from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from app.api.dependencies import current_user, db_session
from app.database.repositories import list_articles

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

@router.get("/articles")
def articles(limit: int = Query(20, ge=1, le=100), user=Depends(current_user), session=Depends(db_session)):
    rows = list_articles(session, limit=limit, order_by_relevance=True)
    return [{"id": a.id, "title": a.title, "source": a.source, "url": a.url, "relevance_score": a.relevance_score} for a in rows]
