"""Tests for app.graph.nodes.

Each node is called directly with a hand-built state and checked for the
partial update it returns -- no graph involved (that is covered by
test_research_graph.py / test_chat_graph.py).
"""

from __future__ import annotations

import pytest

from app.graph import nodes
from app.graph.state import ChatState, ProcessedItem, ResearchState, StageStatus
from app.services.llm_service import LLMServiceError
from app.summarization.structured_output import ArticleSummary

from tests.graph.fakes import (
    FakeAnswerer,
    FakeCollector,
    FakeLLM,
    FakeReranker,
    FakeRetriever,
    RaisingCollector,
    RecordingHook,
    collected,
    doc,
    off_topic_item,
    two_ai_items,
)


def _status(update: dict, stage: str) -> StageStatus:
    (result,) = [s for s in update["stages"] if s.stage == stage]
    return result.status


def _processed_items():
    from app.processing import process_items

    return process_items(two_ai_items())


# --- collect ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collect_pools_items_from_all_collectors_and_reports_counts():
    a = FakeCollector("rss", [collected(url="https://example.com/1")])
    b = FakeCollector("github", [collected(url="https://example.com/2"), collected(url="https://example.com/3")])

    update = await nodes.make_collect_node([a, b])(ResearchState())

    assert len(update["collected_items"]) == 3
    assert update["errors"] == []
    assert _status(update, "collect") == StageStatus.OK
    assert update["stages"][0].detail == "rss=1, github=2"


@pytest.mark.asyncio
async def test_collect_with_no_items_is_empty_not_failed():
    update = await nodes.make_collect_node([FakeCollector("rss", [])])(ResearchState())
    assert update["collected_items"] == []
    assert _status(update, "collect") == StageStatus.EMPTY


@pytest.mark.asyncio
async def test_collect_with_no_collectors_is_empty():
    update = await nodes.make_collect_node([])(ResearchState())
    assert _status(update, "collect") == StageStatus.EMPTY


@pytest.mark.asyncio
async def test_collect_survives_a_collector_that_raises():
    good = FakeCollector("rss", [collected()])
    update = await nodes.make_collect_node([RaisingCollector(), good])(ResearchState())

    assert len(update["collected_items"]) == 1
    assert [e.stage for e in update["errors"]] == ["collect"]
    assert "broken: boom" in update["errors"][0].message
    assert _status(update, "collect") == StageStatus.OK


# --- process ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_process_runs_the_real_pipeline():
    state = ResearchState(collected_items=[*two_ai_items(), off_topic_item()])
    update = await nodes.make_process_node()(state)

    processed = update["processed_items"]
    assert len(processed) == 2  # off-topic item filtered out
    assert all(isinstance(p, ProcessedItem) for p in processed)
    scores = [p.relevance_score for p in processed]
    assert scores == sorted(scores, reverse=True)  # ranked
    assert _status(update, "process") == StageStatus.OK


@pytest.mark.asyncio
async def test_process_with_everything_filtered_is_empty():
    update = await nodes.make_process_node()(ResearchState(collected_items=[off_topic_item()]))
    assert update["processed_items"] == []
    assert _status(update, "process") == StageStatus.EMPTY


@pytest.mark.asyncio
async def test_process_failure_is_recorded_not_raised(monkeypatch):
    def explode(_items):
        raise ValueError("bad pipeline")

    monkeypatch.setattr(nodes, "process_items", explode)
    update = await nodes.make_process_node()(ResearchState(collected_items=[collected()]))

    assert _status(update, "process") == StageStatus.FAILED
    assert update["errors"][0].message == "bad pipeline"


# --- summarize -------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summarize_returns_article_summaries():
    state = ResearchState(processed_items=_processed_items())
    update = await nodes.make_summarize_node(llm=FakeLLM())(state)

    assert len(update["summaries"]) == 2
    assert all(isinstance(s, ArticleSummary) for s in update["summaries"])
    assert update["errors"] == []
    assert _status(update, "summarize") == StageStatus.OK


@pytest.mark.asyncio
async def test_summarize_respects_limit():
    llm = FakeLLM()
    state = ResearchState(processed_items=_processed_items())
    update = await nodes.make_summarize_node(llm=llm, limit=1)(state)

    assert len(update["summaries"]) == 1
    assert len(llm.calls) == 1
    # Summarizes the top-ranked item, since processed_items are ranked.
    assert update["summaries"][0].source_url == state.processed_items[0].url


@pytest.mark.asyncio
async def test_summarize_partial_failure_keeps_successes_and_records_errors():
    items = _processed_items()
    llm = FakeLLM(fail_on=[items[1].title])  # second item's prompt fails
    update = await nodes.make_summarize_node(llm=llm)(ResearchState(processed_items=items))

    assert len(update["summaries"]) == 1
    assert len(update["errors"]) == 1
    assert items[1].url in update["errors"][0].message
    assert _status(update, "summarize") == StageStatus.OK


@pytest.mark.asyncio
async def test_summarize_total_failure_marks_stage_failed():
    llm = FakeLLM(fail_on=["Title:"])  # every prompt fails
    update = await nodes.make_summarize_node(llm=llm)(ResearchState(processed_items=_processed_items()))

    assert update["summaries"] == []
    assert len(update["errors"]) == 2
    assert _status(update, "summarize") == StageStatus.FAILED


@pytest.mark.asyncio
async def test_summarize_records_failure_when_llm_cannot_be_built(monkeypatch):
    def cannot_build():
        raise LLMServiceError("no provider")

    monkeypatch.setattr("app.summarization.summarizer.get_llm_service", cannot_build)
    update = await nodes.make_summarize_node(llm=None)(ResearchState(processed_items=_processed_items()))

    assert _status(update, "summarize") == StageStatus.FAILED
    assert "no provider" in update["errors"][0].message


# --- persist ---------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persist_stores_and_reports_counts(session_scope, db_read):
    items = _processed_items()
    summaries = (await nodes.make_summarize_node(llm=FakeLLM())(ResearchState(processed_items=items)))["summaries"]

    update = await nodes.make_persist_node(session_scope)(
        ResearchState(processed_items=items, summaries=summaries)
    )

    assert update["persisted_articles"] == 2
    assert update["persisted_summaries"] == 2
    assert _status(update, "persist") == StageStatus.OK
    assert len(db_read().articles) == 2


@pytest.mark.asyncio
async def test_persist_failure_is_recorded_not_raised():
    def broken_scope():
        raise RuntimeError("database down")

    update = await nodes.make_persist_node(broken_scope)(ResearchState(processed_items=_processed_items()))

    assert _status(update, "persist") == StageStatus.FAILED
    assert update["errors"][0].message == "database down"


# --- trends / index hooks ------------------------------------------------------------


@pytest.mark.asyncio
async def test_hook_node_without_hook_is_skipped():
    update = await nodes.make_hook_node("trends", None)(ResearchState())
    assert _status(update, "trends") == StageStatus.SKIPPED
    assert "errors" not in update


@pytest.mark.asyncio
async def test_hook_node_calls_hook_with_items_and_summaries():
    hook = RecordingHook()
    items = _processed_items()
    state = ResearchState(processed_items=items)

    update = await nodes.make_hook_node("index", hook)(state)

    assert _status(update, "index") == StageStatus.OK
    assert len(hook.calls) == 1
    assert [i.url for i in hook.calls[0][0]] == [i.url for i in items]


@pytest.mark.asyncio
async def test_hook_node_failure_is_recorded():
    update = await nodes.make_hook_node("trends", RecordingHook(error=RuntimeError("hook broke")))(ResearchState())
    assert _status(update, "trends") == StageStatus.FAILED
    assert update["errors"][0].stage == "trends"


# --- retrieve --------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_returns_documents_and_passes_query_and_top_k():
    retriever = FakeRetriever([doc(1), doc(2)])
    update = await nodes.make_retrieve_node(retriever, top_k=5)(ChatState(query="What is new?"))

    assert [d.title for d in update["retrieved_documents"]] == ["Doc 1", "Doc 2"]
    assert retriever.calls == [("What is new?", 5)]
    assert _status(update, "retrieve") == StageStatus.OK


@pytest.mark.asyncio
async def test_retrieve_with_no_results_is_empty():
    update = await nodes.make_retrieve_node(FakeRetriever([]), top_k=5)(ChatState(query="q"))
    assert update["retrieved_documents"] == []
    assert _status(update, "retrieve") == StageStatus.EMPTY


@pytest.mark.asyncio
async def test_retrieve_without_retriever_fails_clearly():
    update = await nodes.make_retrieve_node(None, top_k=5)(ChatState(query="q"))
    assert _status(update, "retrieve") == StageStatus.FAILED
    assert "No retriever configured" in update["errors"][0].message


@pytest.mark.asyncio
async def test_retrieve_failure_is_recorded_not_raised():
    retriever = FakeRetriever(error=RuntimeError("index unavailable"))
    update = await nodes.make_retrieve_node(retriever, top_k=5)(ChatState(query="q"))
    assert _status(update, "retrieve") == StageStatus.FAILED


# --- rerank ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rerank_without_reranker_is_skipped_and_leaves_documents_alone():
    update = await nodes.make_rerank_node(None)(ChatState(query="q", retrieved_documents=[doc(1)]))
    assert _status(update, "rerank") == StageStatus.SKIPPED
    assert "retrieved_documents" not in update


@pytest.mark.asyncio
async def test_rerank_replaces_documents_with_reranked_order():
    reranker = FakeReranker()
    state = ChatState(query="q", retrieved_documents=[doc(1), doc(2)])
    update = await nodes.make_rerank_node(reranker)(state)

    assert [d.title for d in update["retrieved_documents"]] == ["Doc 2", "Doc 1"]
    assert reranker.calls[0][0] == "q"
    assert _status(update, "rerank") == StageStatus.OK


@pytest.mark.asyncio
async def test_rerank_failure_degrades_to_retrieval_order():
    state = ChatState(query="q", retrieved_documents=[doc(1), doc(2)])
    update = await nodes.make_rerank_node(FakeReranker(error=RuntimeError("model down")))(state)

    assert "retrieved_documents" not in update  # untouched
    assert _status(update, "rerank") == StageStatus.SKIPPED
    assert update["errors"][0].message == "model down"


# --- answer ----------------------------------------------------------------------


@pytest.mark.asyncio
async def test_answer_returns_answer_and_numbered_sources():
    answerer = FakeAnswerer("It launched [1][2].")
    state = ChatState(query="What launched?", retrieved_documents=[doc(1), doc(2)])
    update = await nodes.make_answer_node(answerer)(state)

    assert update["final_answer"] == "It launched [1][2]."
    assert [(s.index, s.title, s.url) for s in update["sources"]] == [
        (1, "Doc 1", "https://example.com/doc1"),
        (2, "Doc 2", "https://example.com/doc2"),
    ]
    assert answerer.calls[0][0] == "What launched?"
    assert _status(update, "answer") == StageStatus.OK


@pytest.mark.asyncio
async def test_answer_without_documents_does_not_call_the_generator():
    answerer = FakeAnswerer()
    update = await nodes.make_answer_node(answerer)(ChatState(query="q"))

    assert update["final_answer"] == nodes.NO_KNOWLEDGE_ANSWER
    assert update["sources"] == []
    assert answerer.calls == []
    assert _status(update, "answer") == StageStatus.EMPTY


@pytest.mark.asyncio
async def test_answer_failure_is_recorded_and_leaves_no_answer():
    answerer = FakeAnswerer(error=LLMServiceError("rate limited"))
    update = await nodes.make_answer_node(answerer)(ChatState(query="q", retrieved_documents=[doc(1)]))

    assert "final_answer" not in update
    assert _status(update, "answer") == StageStatus.FAILED
    assert update["errors"][0].message == "rate limited"
