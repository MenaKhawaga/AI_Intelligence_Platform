"""Tests for app.graph.router -- pure functions, so plain state in / label out."""

from __future__ import annotations

import pytest

from app.graph.router import (
    Workflow,
    route_after_collect,
    route_after_persist,
    route_after_process,
    route_after_retrieve,
    select_workflow,
)
from app.graph.state import ChatState, ProcessedItem, ResearchState, StageResult, StageStatus

from tests.graph.fakes import collected, doc


@pytest.mark.parametrize(
    "query, expected",
    [
        (None, Workflow.RESEARCH),
        ("", Workflow.RESEARCH),
        ("   ", Workflow.RESEARCH),
        ("What did OpenAI release?", Workflow.CHAT),
    ],
)
def test_select_workflow(query, expected):
    assert select_workflow(query) == expected


def test_route_after_collect():
    assert route_after_collect(ResearchState()) == "end"
    assert route_after_collect(ResearchState(collected_items=[collected()])) == "process"


def test_route_after_process():
    assert route_after_process(ResearchState()) == "end"
    item = ProcessedItem.from_collected(collected())
    assert route_after_process(ResearchState(processed_items=[item])) == "summarize"


def test_route_after_persist():
    assert route_after_persist(ResearchState()) == "trends"
    failed = ResearchState(stages=[StageResult(stage="persist", status=StageStatus.FAILED)])
    assert route_after_persist(failed) == "end"


def test_route_after_retrieve():
    assert route_after_retrieve(ChatState(query="q", retrieved_documents=[doc()])) == "rerank"
    assert route_after_retrieve(ChatState(query="q")) == "answer"  # nothing retrieved
    failed = ChatState(query="q", stages=[StageResult(stage="retrieve", status=StageStatus.FAILED)])
    assert route_after_retrieve(failed) == "end"
