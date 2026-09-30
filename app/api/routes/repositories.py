from __future__ import annotations
from fastapi import APIRouter, Depends, Query
from app.api.dependencies import current_user, db_session
from app.database.repositories import list_articles

router = APIRouter(prefix="/repositories", tags=["repositories"])

@router.get("")
def repositories(user=Depends(current_user), session=Depends(db_session), limit: int = Query(20, ge=1, le=100)):
    rows = list_articles(session, source_type="github", limit=limit, order_by_relevance=True)
    return {"items": [{"id": a.id, "title": a.title, "url": a.url, "source": a.source, "score": a.relevance_score, "metadata": a.extra_metadata} for a in rows], "limit": limit}
