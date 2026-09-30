from typing import List, Sequence

from app.graph.state import RetrievedDocument
from app.rag.retriever import search_knowledge_base
from app.rag.reranker import rerank


class LocalRAGRetriever:
    async def retrieve(
        self,
        query: str,
        top_k: int
    ) -> List[RetrievedDocument]:

        results = search_knowledge_base(query, top_k)

        return [
            RetrievedDocument(
                content=result.get("text", ""),
                title=result.get("title", ""),
                source_url=result.get("url", ""),
                score=float(result.get("score", 0)),
                metadata={
                    "id": result.get("id"),
                    "article_id": result.get("article_id"),
                    "source": result.get("source"),
                    "published_at": result.get("published_at"),
                    "category": result.get("category"),
                    "topics": result.get("topics", []),
                },
            )
            for result in results
        ]


class LocalRAGReranker:
    async def rerank(
        self,
        query: str,
        documents: Sequence[RetrievedDocument]
    ) -> List[RetrievedDocument]:

        results = []

        for document in documents:
            results.append({
                "id": document.metadata.get("id"),
                "article_id": document.metadata.get("article_id"),
                "title": document.title,
                "url": document.source_url,
                "text": document.content,
                "source": document.metadata.get("source", ""),
                "published_at": document.metadata.get("published_at"),
                "category": document.metadata.get("category"),
                "topics": document.metadata.get("topics", []),
                "score": document.score,
            })

        reranked = rerank(
            results,
            query,
            limit=len(results)
        )

        return [
            RetrievedDocument(
                content=result.get("text", ""),
                title=result.get("title", ""),
                source_url=result.get("url", ""),
                score=float(result.get("score", 0)),
                metadata={
                    "id": result.get("id"),
                    "article_id": result.get("article_id"),
                    "source": result.get("source"),
                    "published_at": result.get("published_at"),
                    "category": result.get("category"),
                    "topics": result.get("topics", []),
                },
            )
            for result in reranked
        ]