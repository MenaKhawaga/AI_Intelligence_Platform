from __future__ import annotations

import asyncio

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.database.repositories import articles_for_topic, list_articles, list_topics

from app.database.session import get_session
from app.graph.factory import build_production_graph
from app.graph.tools import default_collectors
from app.graph.state import ResearchState
from app.rag.retriever import search_knowledge_base


class SearchArticlesInput(BaseModel):
    query: str = Field(description="Keywords or topic to search for in stored article titles and snippets.")
    limit: int = Field(default=8, ge=1, le=20)


class TopicArticlesInput(BaseModel):
    topic: str = Field(description="Stored topic name.")
    limit: int = Field(default=8, ge=1, le=20)


class ResearchInput(BaseModel):
    reason: str = Field(description="Why fresh research is needed.")

class KnowledgeBaseInput(BaseModel):
    query: str = Field(description="Question or keywords to retrieve from the indexed intelligence knowledge base.")
    limit: int = Field(default=6, ge=1, le=12)


@tool(args_schema=SearchArticlesInput)
def search_articles(query: str, limit: int = 8) -> str:
    """ search in database for articles by simple keyword matching."""

    terms = [term.strip().lower() for term in query.split() if term.strip()]

    with get_session() as session:
        articles = list_articles(session, limit=100, order_by_relevance=True)

        matches = []

        for article in articles:
            haystack = f"{article.title} {article.snippet} {article.source}".lower()

            if not terms or all(term in haystack for term in terms):
                matches.append(article)

            if len(matches) >= limit:
                break

    if not matches:
        return "No stored articles matched the query."
    
    return "\n".join(
        f"[{i}] {article.title} | source={article.source} | url={article.url}\n{article.snippet[:500]}"
        for i, article in enumerate(matches, 1)
                    )


@tool(args_schema=TopicArticlesInput)
def get_topic_articles(topic: str, limit: int = 8) -> str:
    """Return articles in specific topic"""

    with get_session() as session:
        articles = articles_for_topic(session, topic)[:limit]
    
    if not articles:
        return f"No stored articles were found for topic '{topic}'."
    
    return "\n".join(
        f"[{i}] {article.title} | source={article.source} | url={article.url}\n{article.snippet[:500]}"
        for i, article in enumerate(articles, 1)
                    )

@tool
def list_trends() -> str:
    """List topics currently stored by the intelligence pipeline."""

    with get_session() as session:
        topics = list_topics(session)

        if not topics:
            return "No topics have been stored yet."

        results = [
            f"- {topic.name}: {topic.description or 'No description'}; "
            f"last_seen={topic.last_seen_at}"
            for topic in topics
        ]

    return "\n".join(results)


@tool(args_schema=KnowledgeBaseInput)
def search_knowledge_base_tool(query: str, limit: int = 6) -> str:
    """Search the local RAG knowledge base for grounded passages."""

    results = search_knowledge_base(query, limit)

    if not results:
        return "No relevant knowledge-base passages were found."
    
    return "\n".join(
        f"[{i}] {r['title']} | source={r['source']} | url={r['url']} | score={r['score']}\n{r['text'][:700]}"
        for i, r in enumerate(results, 1)
                    )


@tool(args_schema=ResearchInput)
def run_fresh_research(reason: str) -> str:
    """Run the existing research graph to collect and summarize fresh intelligence."""

    graph = build_production_graph(collectors=default_collectors())
    result = asyncio.run(graph.ainvoke(ResearchState()))
    state = ResearchState.model_validate(result)
   
    return (
        f"Fresh research completed for: {reason}. "
        f"Collected={len(state.collected_items)}, processed={len(state.processed_items)}, "
        f"summaries={len(state.summaries)}, persisted_articles={state.persisted_articles}."
    )



agent_tools = [
        search_articles,
        get_topic_articles,
        list_trends,
        search_knowledge_base_tool,
        run_fresh_research,
        ]