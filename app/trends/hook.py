"""Phase 7 — Research-graph hook."""

from __future__ import annotations

from typing import List

from app.graph.tools import SessionScope
from app.graph.state import ResearchState
from app.processing.normalization import ProcessedItem
from app.summarization.structured_output import ArticleSummary
from app.trends.persistence import persist_trends


def make_trends_hook(session_scope: SessionScope):
    """Create the async PipelineHook used by the Phase 6 research graph."""

    async def trends_hook(items: List[ProcessedItem], summaries: List[ArticleSummary]) -> None:
        persist_trends(items, summaries, session_scope=session_scope)

    return trends_hook
