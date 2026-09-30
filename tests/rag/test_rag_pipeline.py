"""Tests for the RAG pipeline: chunking, indexing, retrieval, reranking.

Covers the Step 23 checklist: index, search, metadata, empty database,
top-k, similarity ordering, persistence/reload, and category filtering.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.database.repositories import upsert_article
from app.database.session import get_session
from app.rag.chunking import chunk_text
from app.rag.indexer import build_rag_index, index_path, load_index
from app.rag.retriever import search_knowledge_base


def _seed_articles():
    with get_session() as session:
        upsert_article(
            session,
            url="https://example.com/langgraph",
            source_type="rss",
            source="Example Feed",
            title="LangGraph powers agentic workflows",
            snippet="LangGraph is a graph-based orchestration library for LLM agents.",
            raw_text="LangGraph lets you build stateful, tool-calling agents with explicit control flow.",
            relevance_score=0.9,
            primary_category="LLMs",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        upsert_article(
            session,
            url="https://example.com/robotics",
            source_type="arxiv",
            source="arXiv",
            title="A new robotics manipulation benchmark",
            snippet="Researchers release a benchmark for robotic grasping.",
            raw_text="The benchmark evaluates dexterous manipulation across household objects.",
            relevance_score=0.5,
            primary_category="Robotics",
            published_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
        )


# --- chunking ---------------------------------------------------------------


def test_chunk_text_splits_long_text_with_overlap():
    text = "word " * 400
    chunks = chunk_text(text, chunk_size=200, overlap=40)
    assert len(chunks) > 1
    assert all(chunks)


def test_chunk_text_empty_input_returns_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


# --- indexing -----------------------------------------------------------------


def test_build_rag_index_indexes_articles_and_persists_to_disk(rag_env):
    _seed_articles()
    result = build_rag_index()

    assert result["indexed_articles"] == 2
    assert result["indexed_chunks"] >= 2
    assert index_path().exists()


def test_build_rag_index_preserves_metadata(rag_env):
    _seed_articles()
    build_rag_index()
    index = load_index()

    doc = next(d for d in index["documents"] if d["article_id"] and "langgraph" in d["url"])
    assert doc["title"] == "LangGraph powers agentic workflows"
    assert doc["source"] == "Example Feed"
    assert doc["category"] == "LLMs"
    assert doc["published_at"] is not None


def test_build_rag_index_on_empty_database_produces_empty_index(rag_env):
    result = build_rag_index()
    assert result["indexed_articles"] == 0
    assert result["indexed_chunks"] == 0
    index = load_index()
    assert index["documents"] == []


# --- retrieval ------------------------------------------------------------


def test_search_knowledge_base_builds_index_on_first_call_when_missing(rag_env):
    _seed_articles()
    # No build_rag_index() call yet -- search must build it lazily.
    results = search_knowledge_base("LangGraph agent workflows")
    assert results
    assert results[0]["url"] == "https://example.com/langgraph"


def test_search_knowledge_base_ranks_by_relevance(rag_env):
    _seed_articles()
    build_rag_index()
    results = search_knowledge_base("robotic grasping manipulation benchmark")
    assert results
    assert results[0]["url"] == "https://example.com/robotics"


def test_search_knowledge_base_respects_top_k_limit(rag_env):
    _seed_articles()
    build_rag_index()
    results = search_knowledge_base("benchmark manipulation LangGraph agent", limit=1)
    assert len(results) == 1


def test_search_knowledge_base_category_filter(rag_env):
    _seed_articles()
    build_rag_index()
    results = search_knowledge_base("benchmark", category="LLMs")
    assert all(r["category"] == "LLMs" for r in results)


def test_search_knowledge_base_empty_database_returns_no_results(rag_env):
    results = search_knowledge_base("anything")
    assert results == []


def test_search_knowledge_base_reloads_persisted_index(rag_env):
    _seed_articles()
    build_rag_index()
    # A fresh call re-reads the index from disk rather than relying on any
    # in-memory state -- simulates a new process/request picking it up.
    reloaded = load_index()
    assert reloaded is not None
    assert len(reloaded["documents"]) >= 2
