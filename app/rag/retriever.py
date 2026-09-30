from __future__ import annotations

from app.rag.embeddings import embed_query, cosine
from app.rag.indexer import load_index, build_rag_index
from app.rag.reranker import rerank


def search_knowledge_base(query: str, limit: int = 8, category: str | None = None) -> list[dict]:
    """Search the local knowledge base.

    ``category`` optionally restricts results to chunks whose article
    ``primary_category`` matches exactly (case-insensitive) -- applied
    before reranking/top-k so a filter never displaces relevant results
    with irrelevant ones just because they arrived first.
    """

    index = load_index()
    if not index:
        build_rag_index()
        index = load_index()
    if not index or not index.get("documents"):
        return []
    qv = embed_query(query, index.get("idf", {}))
    results = []
    for doc, vec in zip(index["documents"], index["vectors"]):
        if category and (doc.get("category") or "").lower() != category.lower():
            continue
        item = dict(doc)
        item["score"] = round(cosine(qv, vec), 4)
        results.append(item)
    return rerank(results, query, limit)
