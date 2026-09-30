"""Phase 6 — Graph: routing.

Every decision is a small pure function over state -- no I/O, no LLM, no
randomness -- so what a run will do next can be read straight off the
state. Route functions return a short label; the graph builders map each
label to a node (``"end"`` maps to ``END``).

Choosing a workflow (for callers such as the future API/scheduler):

    select_workflow(query)   -> RESEARCH | CHAT

Research graph branches:

    route_after_collect   nothing collected                 -> end
                          otherwise                         -> process
    route_after_process   nothing survived processing       -> end
                          otherwise                         -> summarize
    route_after_persist   database write failed             -> end
                          otherwise                         -> trends

    (summarize -> persist and trends -> index are unconditional: articles
    are worth storing even if every summary failed.)

Chat graph branches:

    route_after_retrieve  retrieval failed                  -> end   (no answer:
                          claiming "nothing found" would be misleading)
                          nothing retrieved                 -> answer (graceful
                          "no relevant knowledge" reply)
                          otherwise                         -> rerank
"""

from __future__ import annotations

from enum import Enum
from typing import Literal, Optional

from app.graph.state import ChatState, ResearchState


class Workflow(str, Enum):
    RESEARCH = "research"
    CHAT = "chat"


def select_workflow(query: Optional[str]) -> Workflow:
    """A non-blank user question means chat; anything else is the automated research run."""

    return Workflow.CHAT if query and query.strip() else Workflow.RESEARCH


# --- research graph ---------------------------------------------------------


def route_after_collect(state: ResearchState) -> Literal["process", "end"]:
    return "process" if state.collected_items else "end"


def route_after_process(state: ResearchState) -> Literal["summarize", "end"]:
    return "summarize" if state.processed_items else "end"


def route_after_persist(state: ResearchState) -> Literal["trends", "end"]:
    return "end" if state.stage_failed("persist") else "trends"


# --- chat graph -------------------------------------------------------------


def route_after_retrieve(state: ChatState) -> Literal["rerank", "answer", "end"]:
    if state.stage_failed("retrieve"):
        return "end"
    return "rerank" if state.retrieved_documents else "answer"
