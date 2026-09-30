"""Tests for app.graph.state."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.graph.state import (
    ChatState,
    GraphError,
    ResearchState,
    RunStatus,
    StageResult,
    StageStatus,
)


def _stage(name: str, status: StageStatus) -> StageResult:
    return StageResult(stage=name, status=status)


def test_research_state_defaults_are_empty_and_independent():
    a, b = ResearchState(), ResearchState()
    assert a.collected_items == [] and a.processed_items == [] and a.summaries == []
    assert a.persisted_articles == 0 and a.persisted_summaries == 0
    a.stages.append(_stage("collect", StageStatus.OK))
    assert b.stages == []  # no shared mutable default


def test_chat_state_requires_a_query_and_strips_it():
    assert ChatState(query="  what is RAG?  ").query == "what is RAG?"
    with pytest.raises(ValidationError):
        ChatState(query="   ")
    with pytest.raises(ValidationError):
        ChatState()  # type: ignore[call-arg]


def test_stage_status_returns_latest_run_of_a_stage():
    state = ResearchState(
        stages=[_stage("process", StageStatus.FAILED), _stage("process", StageStatus.OK)]
    )
    assert state.stage_status("process") == StageStatus.OK
    assert state.stage_status("collect") is None
    assert not state.stage_failed("process")


def test_stage_failed():
    state = ResearchState(stages=[_stage("persist", StageStatus.FAILED)])
    assert state.stage_failed("persist")


@pytest.mark.parametrize(
    "stages, errors, expected",
    [
        ([], False, RunStatus.COMPLETED),
        ([StageStatus.OK, StageStatus.SKIPPED], False, RunStatus.COMPLETED),
        ([StageStatus.OK], True, RunStatus.COMPLETED_WITH_ERRORS),
        ([StageStatus.OK, StageStatus.EMPTY], True, RunStatus.EMPTY),
        ([StageStatus.EMPTY, StageStatus.FAILED], True, RunStatus.FAILED),
    ],
)
def test_run_status_precedence(stages, errors, expected):
    state = ResearchState(
        stages=[_stage(f"s{i}", s) for i, s in enumerate(stages)],
        errors=[GraphError(stage="x", message="oops")] if errors else [],
    )
    assert state.run_status == expected
