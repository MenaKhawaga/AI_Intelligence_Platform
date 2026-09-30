"""Phase 6 — Graph: typed state models.

Two LangGraph workflows share one small vocabulary (stage log, error log,
run status) and each adds only the fields it actually carries:

    GraphState                     shared: ``stages``, ``errors``, ``run_status``
      |- ResearchState             collected_items -> processed_items -> summaries
      |                            -> persisted counts   (research_graph.py)
      `- ChatState                 query -> retrieved_documents -> final_answer
                                   + sources             (chat_graph.py)

Existing pipeline models are reused, not redefined: ``CollectedItem``
(Phase 2), ``ProcessedItem`` (Phase 3) and ``ArticleSummary`` (Phase 4).
Only the chat side needs new shapes (``RetrievedDocument``,
``SourceReference``) because nothing before Phase 6 represents "a piece of
knowledge retrieved for a question".

How nodes update state
----------------------
Nodes return *partial* updates (a dict of just the fields they changed).
Plain fields are overwritten. ``stages`` and ``errors`` use an ``add``
reducer, so every node simply appends to them and nothing is ever lost or
clobbered -- which is what lets a node record a problem and let the graph
carry on.

``ainvoke`` on a compiled graph returns a plain ``dict``; validate it back
into the typed model with ``ResearchState.model_validate(result)`` (the
``run_research`` / ``run_chat`` helpers do this for you).
"""

from __future__ import annotations

import operator
from enum import Enum
from typing import Annotated, Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from app.collectors.base import CollectedItem
from app.processing.normalization import ProcessedItem
from app.summarization.structured_output import ArticleSummary

__all__ = [
    "CollectedItem",
    "ProcessedItem",
    "ArticleSummary",
    "StageStatus",
    "RunStatus",
    "StageResult",
    "GraphError",
    "RetrievedDocument",
    "SourceReference",
    "GraphState",
    "ResearchState",
    "ChatState",
]


# ---------------------------------------------------------------------------
# Status / error vocabulary
# ---------------------------------------------------------------------------


class StageStatus(str, Enum):
    """Outcome of one node."""

    OK = "ok"  # did its job
    EMPTY = "empty"  # ran fine but had nothing to work on / produced nothing
    SKIPPED = "skipped"  # optional step that was not configured (or degraded)
    FAILED = "failed"  # raised; the error is also recorded in ``errors``


class RunStatus(str, Enum):
    """Overall outcome of a graph run, derived from the stage log."""

    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"  # finished, but something was recorded
    EMPTY = "empty"  # ended early / answered with nothing to go on
    FAILED = "failed"


class StageResult(BaseModel):
    """One line of the run log: which node ran, how it went, and a short note."""

    stage: str
    status: StageStatus
    detail: str = ""


class GraphError(BaseModel):
    """A problem recorded by a node (the graph keeps going unless the router says stop)."""

    stage: str
    message: str


# ---------------------------------------------------------------------------
# Chat-side models
# ---------------------------------------------------------------------------


class RetrievedDocument(BaseModel):
    """One piece of retrieved knowledge handed to the answer step.

    This is the integration contract for the future RAG layer (Phase 8): a
    retriever returns these, a reranker reorders them, the answer step
    grounds on them. ``metadata`` is a free-form escape hatch (chunk id,
    article id, ...) so the RAG layer is not forced to squeeze everything
    into the named fields.
    """

    content: str
    title: str = ""
    source_url: str = ""
    score: float = 0.0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SourceReference(BaseModel):
    """A citable source returned with an answer.

    ``index`` is the 1-based position of the document in the context given
    to the answer step, so an inline citation like ``[2]`` in the answer
    text maps straight to the source with ``index == 2``.
    """

    index: int
    title: str = ""
    url: str = ""


# ---------------------------------------------------------------------------
# Graph states
# ---------------------------------------------------------------------------


class GraphState(BaseModel):
    """Fields and helpers shared by every workflow's state."""

    stages: Annotated[List[StageResult], operator.add] = Field(default_factory=list)
    errors: Annotated[List[GraphError], operator.add] = Field(default_factory=list)

    def stage_status(self, stage: str) -> Optional[StageStatus]:
        """Status of the most recent run of ``stage``, or ``None`` if it never ran."""

        for result in reversed(self.stages):
            if result.stage == stage:
                return result.status
        return None

    def stage_failed(self, stage: str) -> bool:
        return self.stage_status(stage) == StageStatus.FAILED

    @property
    def run_status(self) -> RunStatus:
        """Overall outcome. Precedence: failed > empty > completed_with_errors > completed."""

        statuses = {result.status for result in self.stages}
        if StageStatus.FAILED in statuses:
            return RunStatus.FAILED
        if StageStatus.EMPTY in statuses:
            return RunStatus.EMPTY
        if self.errors:
            return RunStatus.COMPLETED_WITH_ERRORS
        return RunStatus.COMPLETED


class ResearchState(GraphState):
    """State for the automated research pipeline (no user input required).

    Flow: ``collected_items`` -> ``processed_items`` (normalized, cleaned,
    deduplicated, filtered, classified, entity-tagged and ranked by
    ``process_items``) -> ``summaries`` -> stored in the database.
    """

    collected_items: List[CollectedItem] = Field(default_factory=list)
    processed_items: List[ProcessedItem] = Field(default_factory=list)
    summaries: List[ArticleSummary] = Field(default_factory=list)
    persisted_articles: int = 0
    persisted_summaries: int = 0


class ChatState(GraphState):
    """State for answering one user question."""

    query: str
    retrieved_documents: List[RetrievedDocument] = Field(default_factory=list)
    final_answer: Optional[str] = None
    sources: List[SourceReference] = Field(default_factory=list)

    @field_validator("query")
    @classmethod
    def _query_not_blank(cls, value: str) -> str:
        # Reject bad input at the graph boundary instead of routing around it.
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value
