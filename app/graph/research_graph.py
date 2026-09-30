"""Phase 6 — Graph: the automated research/intelligence workflow.

    START
      -> collect      run all collectors, pool CollectedItems
      -> process      normalize/clean/dedupe/filter/classify/entities/rank
      -> summarize    LLM summaries for the top-ranked items
      -> persist      store articles + summaries (Phase 5 database)
      -> trends       integration point (Phase 7)   -- skipped if no hook
      -> index        integration point (Phase 8)   -- skipped if no hook
      -> END

Conditional exits (see router.py): nothing collected, nothing left after
processing, or a failed database write end the run early.

Ranking is the last step of ``process_items`` (Phase 3), so it happens
inside the ``process`` node rather than as a separate node.
"""

from __future__ import annotations

from typing import Optional, Sequence

from langgraph.graph import END, START, StateGraph

from app.collectors.base import BaseCollector
from app.database.session import get_session
from app.graph import nodes
from app.graph.router import route_after_collect, route_after_persist, route_after_process
from app.graph.state import ResearchState
from app.graph.tools import PipelineHook, SessionScope, default_collectors
from app.services.llm_service import LLMService


def build_research_graph(
    *,
    collectors: Optional[Sequence[BaseCollector]] = None,
    llm: Optional[LLMService] = None,
    summary_limit: Optional[int] = None,
    session_scope: SessionScope = get_session,
    trends_hook: Optional[PipelineHook] = None,
    index_hook: Optional[PipelineHook] = None,
):
    """Build and compile the research graph.

    Args:
        collectors: sources to run; defaults to ``default_collectors()``.
        llm: ``LLMService`` for summarization; defaults to the configured one.
        summary_limit: summarize only the top-N ranked items (cost control).
        session_scope: database session context manager; defaults to ``get_session``.
        trends_hook / index_hook: optional Phase 7 / Phase 8 integration points.
    """

    if collectors is None:
        collectors = default_collectors()

    graph = StateGraph(ResearchState)

    graph.add_node(nodes.COLLECT, nodes.make_collect_node(collectors))
    graph.add_node(nodes.PROCESS, nodes.make_process_node())
    graph.add_node(nodes.SUMMARIZE, nodes.make_summarize_node(llm=llm, limit=summary_limit))
    graph.add_node(nodes.PERSIST, nodes.make_persist_node(session_scope))
    graph.add_node(nodes.TRENDS, nodes.make_hook_node(nodes.TRENDS, trends_hook))
    graph.add_node(nodes.INDEX, nodes.make_hook_node(nodes.INDEX, index_hook))

    graph.add_edge(START, nodes.COLLECT)
    graph.add_conditional_edges(
        nodes.COLLECT, route_after_collect, {"process": nodes.PROCESS, "end": END}
    )
    graph.add_conditional_edges(
        nodes.PROCESS, route_after_process, {"summarize": nodes.SUMMARIZE, "end": END}
    )
    graph.add_edge(nodes.SUMMARIZE, nodes.PERSIST)
    graph.add_conditional_edges(
        nodes.PERSIST, route_after_persist, {"trends": nodes.TRENDS, "end": END}
    )
    graph.add_edge(nodes.TRENDS, nodes.INDEX)
    graph.add_edge(nodes.INDEX, END)

    return graph.compile()


async def run_research(compiled_graph) -> ResearchState:
    """Run a compiled research graph once and return the final typed state."""

    result = await compiled_graph.ainvoke(ResearchState())
    return ResearchState.model_validate(result)
