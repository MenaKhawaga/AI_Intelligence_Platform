"""End-to-end tests for the chat graph, with fake retriever/reranker/LLM."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.graph.chat_graph import build_chat_graph, run_chat
from app.graph.nodes import NO_KNOWLEDGE_ANSWER
from app.graph.state import ChatState, RunStatus, StageStatus
from app.graph.tools import LLMAnswerGenerator
from app.services.llm_service import LLMServiceError

from tests.graph.fakes import FakeAnswerer, FakeLLM, FakeReranker, FakeRetriever, doc


def _stages(state: ChatState) -> dict:
    return {s.stage: s.status for s in state.stages}


@pytest.mark.asyncio
async def test_question_flows_retrieve_rerank_answer_with_sources():
    retriever, reranker, answerer = FakeRetriever([doc(1), doc(2)]), FakeReranker(), FakeAnswerer("Answer [1].")
    graph = build_chat_graph(retriever=retriever, reranker=reranker, answerer=answerer, top_k=4)

    state = await run_chat(graph, "  What launched this week? ")

    assert state.query == "What launched this week?"
    assert state.final_answer == "Answer [1]."
    assert [s.stage for s in state.stages] == ["retrieve", "rerank", "answer"]
    assert state.run_status == RunStatus.COMPLETED
    assert retriever.calls == [("What launched this week?", 4)]

    # The answer step saw the *reranked* order, and sources match that order.
    assert [d.title for d in answerer.calls[0][1]] == ["Doc 2", "Doc 1"]
    assert [(s.index, s.title) for s in state.sources] == [(1, "Doc 2"), (2, "Doc 1")]


@pytest.mark.asyncio
async def test_rerank_is_optional():
    answerer = FakeAnswerer()
    graph = build_chat_graph(retriever=FakeRetriever([doc(1), doc(2)]), answerer=answerer)

    state = await run_chat(graph, "q")

    assert _stages(state)["rerank"] == StageStatus.SKIPPED
    assert [d.title for d in answerer.calls[0][1]] == ["Doc 1", "Doc 2"]  # retrieval order kept
    assert state.run_status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_failing_reranker_still_yields_an_answer():
    graph = build_chat_graph(
        retriever=FakeRetriever([doc(1)]),
        reranker=FakeReranker(error=RuntimeError("model down")),
        answerer=FakeAnswerer("Still answered."),
    )

    state = await run_chat(graph, "q")

    assert state.final_answer == "Still answered."
    assert state.run_status == RunStatus.COMPLETED_WITH_ERRORS
    assert state.errors[0].stage == "rerank"


@pytest.mark.asyncio
async def test_no_relevant_knowledge_gives_graceful_answer_without_calling_llm():
    llm = FakeLLM()
    reranker = FakeReranker()
    # The real default answerer on a fake LLM, to prove the LLM is never called.
    graph = build_chat_graph(retriever=FakeRetriever([]), reranker=reranker, answerer=LLMAnswerGenerator(llm))

    state = await run_chat(graph, "Something obscure?")

    assert state.final_answer == NO_KNOWLEDGE_ANSWER
    assert state.sources == []
    assert [s.stage for s in state.stages] == ["retrieve", "answer"]  # rerank skipped: nothing to rerank
    assert reranker.calls == [] and llm.calls == []
    assert state.run_status == RunStatus.EMPTY


@pytest.mark.asyncio
async def test_retrieval_failure_ends_the_run_without_an_answer():
    answerer = FakeAnswerer()
    graph = build_chat_graph(retriever=FakeRetriever(error=RuntimeError("index unavailable")), answerer=answerer)

    state = await run_chat(graph, "q")

    assert state.final_answer is None
    assert [s.stage for s in state.stages] == ["retrieve"]
    assert state.run_status == RunStatus.FAILED
    assert answerer.calls == []


@pytest.mark.asyncio
async def test_without_a_retriever_the_run_fails_clearly():
    state = await run_chat(build_chat_graph(answerer=FakeAnswerer()), "q")

    assert state.final_answer is None
    assert state.run_status == RunStatus.FAILED
    assert "No retriever configured" in state.errors[0].message


@pytest.mark.asyncio
async def test_answer_failure_is_reported():
    graph = build_chat_graph(
        retriever=FakeRetriever([doc(1)]), answerer=FakeAnswerer(error=LLMServiceError("rate limited"))
    )

    state = await run_chat(graph, "q")

    assert state.final_answer is None
    assert state.sources == []
    assert state.run_status == RunStatus.FAILED
    assert state.errors[0].message == "rate limited"


@pytest.mark.asyncio
async def test_default_answerer_grounds_on_retrieved_documents():
    llm = FakeLLM(response="Grounded [1].")
    graph = build_chat_graph(retriever=FakeRetriever([doc(1)]), answerer=LLMAnswerGenerator(llm))
    state = await run_chat(graph, "Why?")

    assert state.final_answer == "Grounded [1]."
    assert "Content of document 1." in llm.calls[0]["user"]


@pytest.mark.asyncio
async def test_blank_question_is_rejected():
    graph = build_chat_graph(retriever=FakeRetriever([doc(1)]), answerer=FakeAnswerer())
    with pytest.raises(ValidationError):
        await run_chat(graph, "   ")
