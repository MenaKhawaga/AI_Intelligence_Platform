from __future__ import annotations
from collections import Counter
from fastapi import APIRouter, Depends
from app.api.dependencies import current_user, db_session
from app.database.repositories import list_articles, list_topics

router = APIRouter(prefix="/analytics", tags=["analytics"])

@router.get("/overview")
def overview(user=Depends(current_user), session=Depends(db_session)):

    articles = list_articles(session, limit=5000, order_by_relevance=False)
    sources = Counter(a.source or "unknown" for a in articles)
    categories = Counter(a.primary_category or "Uncategorized" for a in articles)
    
    return {
        "total_articles": len(articles),
        "total_topics": len(list_topics(session)),
        "sources": dict(sources),
        "categories": dict(categories),
        "average_relevance": round(sum(a.relevance_score for a in articles) / len(articles), 3) if articles else 0,
        "recent_intelligence": [{"id": a.id, "title": a.title, "source": a.source, "url": a.url, "relevance_score": a.relevance_score} for a in articles[:10]],
    }
