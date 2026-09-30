"""Tests for app.graph.tools."""

from __future__ import annotations

import pytest

from app.collectors.base import BaseCollector
from app.graph.state import ProcessedItem
from app.graph.tools import (
    ANSWER_SYSTEM_PROMPT,
    MAX_DOC_CHARS,
    LLMAnswerGenerator,
    build_answer_prompt,
    default_collectors,
    persist_results,
)
from app.services.llm_service import LLMServiceError
from app.summarization.structured_output import ArticleSummary

from tests.graph.fakes import FakeLLM, collected, doc


def _processed(**overrides) -> ProcessedItem:
    item = ProcessedItem.from_collected(collected(**overrides))
    item.primary_category = "LLMs"
    item.categories = ["LLMs"]
    item.entities = {"companies": ["OpenAI"]}
    item.relevance_score = 80.0
    return item


def _summary_for(item: ProcessedItem, headline: str = "Headline") -> ArticleSummary:
    return ArticleSummary(
        headline=headline,
        summary="Summary text.",
        key_points=["a", "b"],
        why_it_matters="Because.",
        category="LLMs",
        source_url=item.url,
    )


# --- default_collectors ------------------------------------------------------


def test_default_collectors_are_the_five_sources():
    collectors = default_collectors()
    assert all(isinstance(c, BaseCollector) for c in collectors)
    assert {c.source_type for c in collectors} == {"rss", "github", "hackernews", "arxiv", "reddit"}


# --- persist_results ---------------------------------------------------------


def test_persist_results_stores_articles_and_summaries(session_scope, db_read):
    item = _processed()
    result = persist_results([item], [_summary_for(item)], session_scope)

    assert (result.articles, result.summaries) == (1, 1)
    stored = db_read()
    assert [a.url for a in stored.articles] == [item.url]
    article = stored.articles[0]
    assert article.title == item.title
    assert article.primary_category == "LLMs"
    assert article.relevance_score == 80.0
    assert article.native_score == 250
    assert [c.name for c in article.categories] == ["LLMs"]
    assert [e.name for e in article.entities] == ["OpenAI"]
    assert stored.summaries[0].headline == "Headline"
    assert stored.summaries[0].key_points == ["a", "b"]


def test_persist_results_is_idempotent(session_scope, db_read):
    item = _processed()
    persist_results([item], [_summary_for(item, "First")], session_scope)
    persist_results([item], [_summary_for(item, "Second")], session_scope)

    stored = db_read()
    assert len(stored.articles) == 1
    assert len(stored.summaries) == 1
    assert stored.summaries[0].headline == "Second"  # updated in place, not duplicated


def test_persist_results_without_summaries_still_stores_articles(session_scope, db_read):
    result = persist_results([_processed()], [], session_scope)
    assert (result.articles, result.summaries) == (1, 0)
    assert len(db_read().articles) == 1


def test_persist_results_skips_summary_without_article(session_scope, db_read):
    item = _processed()
    orphan = _summary_for(_processed(url="https://example.com/other"))
    result = persist_results([item], [orphan], session_scope)

    assert (result.articles, result.summaries) == (1, 0)
    assert db_read().summaries == []


def test_persist_results_is_atomic(session_scope, db_read):
    good = _processed()
    bad = _processed(url="https://example.com/bad", metadata={"unserializable": {1, 2}})

    with pytest.raises(Exception):
        persist_results([good, bad], [], session_scope)

    assert db_read().articles == []  # the good article was rolled back too


# --- grounded answer prompt / generator ----------------------------------------


def test_build_answer_prompt_numbers_sources_and_includes_question():
    prompt = build_answer_prompt("What happened?", [doc(1), doc(2, title="", source_url="")])

    assert "QUESTION: What happened?" in prompt
    assert "[1] Doc 1 (https://example.com/doc1)\nContent of document 1." in prompt
    assert "[2] Untitled\nContent of document 2." in prompt


def test_build_answer_prompt_truncates_long_content():
    prompt = build_answer_prompt("q", [doc(1, content="x" * (MAX_DOC_CHARS + 500))])
    assert "x" * MAX_DOC_CHARS in prompt
    assert "x" * (MAX_DOC_CHARS + 1) not in prompt
    assert "[truncated]" in prompt


@pytest.mark.asyncio
async def test_llm_answer_generator_uses_grounded_prompts():
    llm = FakeLLM(response="Grounded answer [1].")
    answer = await LLMAnswerGenerator(llm).generate("Why?", [doc(1)])

    assert answer == "Grounded answer [1]."
    assert llm.calls[0]["system"] == ANSWER_SYSTEM_PROMPT
    assert "QUESTION: Why?" in llm.calls[0]["user"]
    assert "Content of document 1." in llm.calls[0]["user"]


@pytest.mark.asyncio
async def test_llm_answer_generator_propagates_llm_errors():
    llm = FakeLLM(fail_on=["QUESTION"])
    with pytest.raises(LLMServiceError):
        await LLMAnswerGenerator(llm).generate("Why?", [doc(1)])
