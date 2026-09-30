from __future__ import annotations

import json
from pathlib import Path
from app.core.config import settings
from app.database.repositories import list_articles
from app.database.session import get_session
from app.rag.chunking import chunk_text
from app.rag.embeddings import build_index


def index_path() -> Path:
    path = Path(settings.CHROMA_PATH)
    if path.suffix:
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    path.mkdir(parents=True, exist_ok=True)
    return path / "local_vector_index.json"


def build_rag_index(limit: int = 1000) -> dict:
    documents = []
    with get_session() as session:
        articles = list_articles(session, limit=limit, order_by_relevance=True)
        for article in articles:
            text = " ".join(filter(None, [article.title, article.snippet, article.raw_text]))
            published_at = article.published_at.isoformat() if article.published_at else None
            topics = [t.name for t in article.topics]
            for i, chunk in enumerate(chunk_text(text)):
                documents.append(
                    {
                        "id": f"article-{article.id}-{i}",
                        "article_id": article.id,
                        "title": article.title,
                        "source": article.source,
                        "url": article.url,
                        "text": chunk,
                        # Preserved so the retriever/UI can show and filter on
                        # more than just title/source/url (spec Step 8).
                        "published_at": published_at,
                        "category": article.primary_category,
                        "topics": topics,
                    }
                )
    index = build_index(documents)
    path = index_path()
    path.write_text(json.dumps(index, ensure_ascii=False), encoding="utf-8")
    return {"indexed_articles": len(articles), "indexed_chunks": len(documents), "path": str(path)}


def load_index() -> dict | None:
    path = index_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
