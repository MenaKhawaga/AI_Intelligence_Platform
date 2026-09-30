"""Phase 7/12 — Production graph wiring.

``build_research_graph`` (Phase 6) takes ``trends_hook`` / ``index_hook`` as
plain optional arguments and does nothing on its own to wire them up -- that
was deliberately left to whoever calls it. Three call sites need the same
answer (the manual "/research/run" endpoint, the agent's "run_fresh_research"
tool, and the hourly scheduler), so this module is the one place that
decides it: every real run should persist trends, not just articles.

Without this, ``build_research_graph()`` runs with no ``trends_hook``, the
``trends`` stage is recorded as "skipped", and the Trends page stays empty
forever even though research keeps completing successfully.
"""

from __future__ import annotations

from typing import Optional, Sequence

from app.collectors.base import BaseCollector
from app.database.session import get_session
from app.graph.research_graph import build_research_graph
from app.trends.hook import make_trends_hook


def build_production_graph(
    *,
    collectors: Optional[Sequence[BaseCollector]] = None,
    summary_limit: Optional[int] = None,
):
    """``build_research_graph`` with the Phase 7 trends hook always wired in."""

    return build_research_graph(
        collectors=collectors,
        summary_limit=summary_limit,
        trends_hook=make_trends_hook(get_session),
    )
