"""End-to-end tests for the research graph.

Collectors and the LLM are fakes; processing and the database are the
real Phase 3 / Phase 5 code (in-memory SQLite). No network involved.
"""

from __future__ import annotations

import pytest

from app.graph.research_graph import build_research_graph, run_research
from app.graph.state import ResearchState, RunStatus, StageStatus

from tests.graph.fakes import (
    FakeCollector,
    FakeLLM,
    RaisingCollector,
    RecordingHook,
    off_topic_item,
    two_ai_items,
)


def _stages(state: ResearchState) -> dict:
    return {s.stage: s.status for s in state.stages}


def _build(session_scope, **overrides):
    kwargs = dict(
        collectors=[FakeCollector("rss", two_ai_items()), FakeCollector("reddit", [off_topic_item()])],
        llm=FakeLLM(),
        session_scope=session_scope,
    )
    kwargs.update(overrides)
    return build_research_graph(**kwargs)


@pytest.mark.asyncio
async def test_full_pipeline_runs_every_stage_in_order(session_scope, db_read):
    state = await run_research(_build(session_scope))

    assert [s.stage for s in state.stages] == [
        "collect", "process", "summarize", "persist", "trends", "index",
    ]
    assert _stages(state) == {
        "collect": StageStatus.OK,
        "process": StageStatus.OK,
        "summarize": StageStatus.OK,
        "persist": StageStatus.OK,
        "trends": StageStatus.SKIPPED,  # no hooks configured
        "index": StageStatus.SKIPPED,
    }
    assert state.run_status == RunStatus.COMPLETED

    assert len(state.collected_items) == 3
    assert len(state.processed_items) == 2  # off-topic item filtered by the real pipeline
    assert len(state.summaries) == 2
    assert (state.persisted_articles, state.persisted_summaries) == (2, 2)

    stored = db_read()
    assert len(stored.articles) == 2
    assert len(stored.summaries) == 2


@pytest.mark.asyncio
async def test_hooks_run_after_persist_with_processed_items_and_summaries(session_scope):
    trends, index = RecordingHook(), RecordingHook()
    state = await run_research(_build(session_scope, trends_hook=trends, index_hook=index))

    for hook in (trends, index):
        assert len(hook.calls) == 1
        items, summaries = hook.calls[0]
        assert len(items) == 2 and len(summaries) == 2
    assert _stages(state)["trends"] == StageStatus.OK
    assert _stages(state)["index"] == StageStatus.OK
    assert state.run_status == RunStatus.COMPLETED


@pytest.mark.asyncio
async def test_summary_limit_caps_llm_calls(session_scope, db_read):
    llm = FakeLLM()
    state = await run_research(_build(session_scope, llm=llm, summary_limit=1))

    assert len(llm.calls) == 1
    assert (state.persisted_articles, state.persisted_summaries) == (2, 1)  # both articles kept


@pytest.mark.asyncio
async def test_run_ends_early_when_nothing_is_collected(session_scope, db_read):
    llm = FakeLLM()
    state = await run_research(_build(session_scope, collectors=[FakeCollector("rss", [])], llm=llm))

    assert [s.stage for s in state.stages] == ["collect"]
    assert state.run_status == RunStatus.EMPTY
    assert llm.calls == []
    assert db_read().articles == []


@pytest.mark.asyncio
async def test_run_ends_early_when_everything_is_filtered_out(session_scope):
    llm = FakeLLM()
    state = await run_research(
        _build(session_scope, collectors=[FakeCollector("reddit", [off_topic_item()])], llm=llm)
    )

    assert [s.stage for s in state.stages] == ["collect", "process"]
    assert _stages(state)["process"] == StageStatus.EMPTY
    assert llm.calls == []


@pytest.mark.asyncio
async def test_summarization_failures_do_not_stop_persistence(session_scope, db_read):
    state = await run_research(_build(session_scope, llm=FakeLLM(fail_on=["Title:"])))

    assert state.summaries == []
    assert _stages(state)["summarize"] == StageStatus.FAILED
    assert _stages(state)["persist"] == StageStatus.OK  # articles still stored
    assert state.run_status == RunStatus.FAILED
    assert len(state.errors) == 2
    assert len(db_read().articles) == 2
    assert db_read().summaries == []


@pytest.mark.asyncio
async def test_persist_failure_stops_before_hooks():
    from contextlib import contextmanager

    @contextmanager
    def broken_scope():
        raise RuntimeError("database down")
        yield  # pragma: no cover

    trends, index = RecordingHook(), RecordingHook()
    state = await run_research(
        build_research_graph(
            collectors=[FakeCollector("rss", two_ai_items())],
            llm=FakeLLM(),
            session_scope=broken_scope,
            trends_hook=trends,
            index_hook=index,
        )
    )

    assert _stages(state)["persist"] == StageStatus.FAILED
    assert "trends" not in _stages(state) and "index" not in _stages(state)
    assert trends.calls == [] and index.calls == []
    assert state.run_status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_failing_hook_is_recorded_and_the_run_continues(session_scope):
    index = RecordingHook()
    state = await run_research(
        _build(session_scope, trends_hook=RecordingHook(error=RuntimeError("trends broke")), index_hook=index)
    )

    assert _stages(state)["trends"] == StageStatus.FAILED
    assert _stages(state)["index"] == StageStatus.OK
    assert len(index.calls) == 1
    assert state.run_status == RunStatus.FAILED


@pytest.mark.asyncio
async def test_one_broken_collector_does_not_sink_the_run(session_scope):
    state = await run_research(
        _build(session_scope, collectors=[RaisingCollector(), FakeCollector("rss", two_ai_items())])
    )

    assert state.persisted_articles == 2
    assert any(e.stage == "collect" for e in state.errors)
    assert state.run_status == RunStatus.COMPLETED_WITH_ERRORS


@pytest.mark.asyncio
async def test_rerunning_the_pipeline_updates_instead_of_duplicating(session_scope, db_read):
    graph = _build(session_scope)
    await run_research(graph)
    await run_research(graph)

    stored = db_read()
    assert len(stored.articles) == 2
    assert len(stored.summaries) == 2
