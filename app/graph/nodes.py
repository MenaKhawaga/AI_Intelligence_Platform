"""Phase 6 — Graph: nodes.

Each node is deliberately thin: read what it needs from state, make ONE
call into existing code, translate the outcome into a partial state
update. All real logic stays where it already lives:

    collect    -> BaseCollector.collect()        (app/collectors)
    process    -> process_items()                (app/processing; includes ranking)
    summarize  -> summarize_items()              (app/summarization)
    persist    -> persist_results()              (tools.py -> app/database)
    trends     -> injected hook                  (Phase 7 plugs in)
    index      -> injected hook                  (Phase 8 plugs in)
    retrieve   -> Retriever.retrieve()           (Phase 8 plugs in)
    rerank     -> Reranker.rerank()              (Phase 8 plugs in)
    answer     -> AnswerGenerator.generate()     (tools.py default: LLMService)

Dependencies are injected through ``make_*_node`` factories, so nodes are
plain closures: no globals, and tests swap in fakes without patching.

Error policy: a node never lets an exception escape. It records a
``GraphError`` plus a ``FAILED`` stage and returns; the router decides
whether the run can continue.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional, Sequence

from app.collectors.base import BaseCollector
from app.graph.state import (
    ChatState,
    GraphError,
    ResearchState,
    RetrievedDocument,
    SourceReference,
    StageResult,
    StageStatus,
)
from app.graph.tools import AnswerGenerator, PipelineHook, Reranker, Retriever, SessionScope, persist_results
from app.processing import process_items
from app.services.llm_service import LLMService
from app.summarization.summarizer import summarize_items

from app.services.n8n_service import send_high_relevance_article_alert

logger = logging.getLogger(__name__)

# Node names, shared with the graph builders.
COLLECT = "collect"
PROCESS = "process"
SUMMARIZE = "summarize"
PERSIST = "persist"
TRENDS = "trends"
INDEX = "index"
RETRIEVE = "retrieve"
RERANK = "rerank"
ANSWER = "answer"

#: Returned (without calling the LLM) when nothing relevant was retrieved,
#: so the chat flow never answers from thin air.
NO_KNOWLEDGE_ANSWER = "I couldn't find relevant information in the knowledge base to answer that question."

Update = Dict[str, Any]


def _stage(stage: str, status: StageStatus, detail: str = "") -> List[StageResult]:
    return [StageResult(stage=stage, status=status, detail=detail)]


def _failure(stage: str, exc: BaseException) -> Update:
    logger.error("Graph stage '%s' failed: %s", stage, exc)
    message = str(exc) or type(exc).__name__
    return {
        "errors": [GraphError(stage=stage, message=message)],
        "stages": _stage(stage, StageStatus.FAILED, message),
    }


# ---------------------------------------------------------------------------
# Research graph nodes
# ---------------------------------------------------------------------------


def make_collect_node(collectors: Sequence[BaseCollector]) -> Callable[[ResearchState], Awaitable[Update]]:
    """Run every collector concurrently and pool their ``CollectedItem``s."""

    async def collect_node(state: ResearchState) -> Update:
        if not collectors:
            return {"stages": _stage(COLLECT, StageStatus.EMPTY, "no collectors configured")}

        results = await asyncio.gather(*(c.collect() for c in collectors), return_exceptions=True)

        items: list = []
        errors: List[GraphError] = []
        counts: List[str] = []
        for collector, result in zip(collectors, results):
            # ``collect()`` is contractually non-raising; this only guards custom collectors.
            if isinstance(result, BaseException):
                errors.append(GraphError(stage=COLLECT, message=f"{collector.source_type}: {result}"))
                counts.append(f"{collector.source_type}=error")
                continue
            items.extend(result)
            counts.append(f"{collector.source_type}={len(result)}")

        status = StageStatus.OK if items else StageStatus.EMPTY
        return {
            "collected_items": items,
            "errors": errors,
            "stages": _stage(COLLECT, status, ", ".join(counts)),
        }

    return collect_node


def make_process_node() -> Callable[[ResearchState], Awaitable[Update]]:
    """Normalize -> clean -> dedupe -> filter -> classify -> entities -> rank, via ``process_items``."""

    async def process_node(state: ResearchState) -> Update:
        try:
            processed = process_items(state.collected_items)
        except Exception as exc:  # noqa: BLE001 - node boundary, see module docstring
            return _failure(PROCESS, exc)

        status = StageStatus.OK if processed else StageStatus.EMPTY
        detail = f"{len(state.collected_items)} collected -> {len(processed)} processed"
        return {"processed_items": processed, "stages": _stage(PROCESS, status, detail)}

    return process_node


def make_summarize_node(
    llm: Optional[LLMService] = None, limit: Optional[int] = None
) -> Callable[[ResearchState], Awaitable[Update]]:
    """Summarize the top-ranked items via ``summarize_items`` (which never raises per item).

    Items whose summarization failed are reported in ``errors`` but do not
    stop the run -- their articles are still persisted, just without a summary.
    """

    async def summarize_node(state: ResearchState) -> Update:
        try:
            results = await summarize_items(state.processed_items, llm=llm, limit=limit)
        except Exception as exc:  # noqa: BLE001 - e.g. LLM service could not be constructed
            return _failure(SUMMARIZE, exc)

        summaries = [r.summary for r in results if r.ok]
        errors = [GraphError(stage=SUMMARIZE, message=f"{r.item.url}: {r.error}") for r in results if not r.ok]
        # Every summarization failing is a failed stage (per-item errors are already in
        # ``errors``); partial failure still counts as OK. Either way the router continues
        # to persist, so the articles themselves are not lost.
        status = StageStatus.FAILED if results and not summaries else StageStatus.OK
        return {
            "summaries": summaries,
            "errors": errors,
            "stages": _stage(SUMMARIZE, status, f"{len(summaries)}/{len(results)} summarized"),
        }

    return summarize_node


def make_persist_node(session_scope: SessionScope) -> Callable[[ResearchState], Awaitable[Update]]:
    """Store articles and summaries through the Phase 5 repositories."""

    async def persist_node(state: ResearchState) -> Update:
        try:
            result = persist_results(state.processed_items, state.summaries, session_scope)

            # Send n8n alert for high-relevance articles
            for item in state.processed_items:
                if item.relevance_score > 0.8:
                    article_id = result.article_ids.get(item.url)

                    if article_id is None:
                        continue

                    await send_high_relevance_article_alert(
                        article_id=article_id,
                        title=item.title,
                        source=item.source,
                        relevance_score=item.relevance_score,
                        url=item.url,
                        summary=item.summary,
                    )

        except Exception as exc:  # noqa: BLE001 - DB errors vary by backend
            return _failure(PERSIST, exc)

        return {
            "persisted_articles": result.articles,
            "persisted_summaries": result.summaries,
            "stages": _stage(PERSIST, StageStatus.OK, f"{result.articles} article(s), {result.summaries} summary(ies)"),
        }

    return persist_node


def make_hook_node(stage: str, hook: Optional[PipelineHook]) -> Callable[[ResearchState], Awaitable[Update]]:
    """An optional integration point after persistence (used for ``trends`` and ``index``).

    With no hook configured the stage is recorded as ``skipped`` and the
    run continues. A hook that raises is recorded as failed; it cannot
    undo what was already stored.
    """

    async def hook_node(state: ResearchState) -> Update:
        if hook is None:
            return {"stages": _stage(stage, StageStatus.SKIPPED, "no hook configured")}
        try:
            await hook(state.processed_items, state.summaries)
        except Exception as exc:  # noqa: BLE001 - hooks are foreign code
            return _failure(stage, exc)
        return {"stages": _stage(stage, StageStatus.OK)}

    return hook_node


# ---------------------------------------------------------------------------
# Chat graph nodes
# ---------------------------------------------------------------------------


def make_retrieve_node(retriever: Optional[Retriever], top_k: int) -> Callable[[ChatState], Awaitable[Update]]:
    """Fetch candidate knowledge for the question."""

    async def retrieve_node(state: ChatState) -> Update:
        if retriever is None:
            return _failure(RETRIEVE, RuntimeError("No retriever configured (RAG arrives in Phase 8)"))
        try:
            documents = await retriever.retrieve(state.query, top_k)
        except Exception as exc:  # noqa: BLE001 - vector store / embedding errors
            return _failure(RETRIEVE, exc)

        status = StageStatus.OK if documents else StageStatus.EMPTY
        return {
            "retrieved_documents": list(documents),
            "stages": _stage(RETRIEVE, status, f"{len(documents)} document(s)"),
        }

    return retrieve_node


def make_rerank_node(reranker: Optional[Reranker]) -> Callable[[ChatState], Awaitable[Update]]:
    """Reorder retrieved documents, if a reranker is available.

    Reranking only improves quality, so it degrades gracefully: with no
    reranker the retrieval order is kept; if the reranker fails the error
    is recorded and the retrieval order is kept.
    """

    async def rerank_node(state: ChatState) -> Update:
        if reranker is None:
            return {"stages": _stage(RERANK, StageStatus.SKIPPED, "no reranker configured")}
        try:
            reranked = await reranker.rerank(state.query, state.retrieved_documents)
        except Exception as exc:  # noqa: BLE001 - reranker is foreign code
            logger.warning("Reranker failed, keeping retrieval order: %s", exc)
            return {
                "errors": [GraphError(stage=RERANK, message=str(exc) or type(exc).__name__)],
                "stages": _stage(RERANK, StageStatus.SKIPPED, "reranker failed; kept retrieval order"),
            }
        return {
            "retrieved_documents": list(reranked),
            "stages": _stage(RERANK, StageStatus.OK, f"{len(reranked)} document(s)"),
        }

    return rerank_node


def _build_sources(documents: Sequence[RetrievedDocument]) -> List[SourceReference]:
    # Same order and numbering as the context the answer step was given,
    # so inline [n] citations line up with ``index``.
    return [
        SourceReference(index=i, title=doc.title, url=doc.source_url) for i, doc in enumerate(documents, start=1)
    ]


def make_answer_node(answerer: AnswerGenerator) -> Callable[[ChatState], Awaitable[Update]]:
    """Generate a grounded answer and return the sources it was grounded on."""

    async def answer_node(state: ChatState) -> Update:
        documents = state.retrieved_documents
        if not documents:
            return {
                "final_answer": NO_KNOWLEDGE_ANSWER,
                "sources": [],
                "stages": _stage(ANSWER, StageStatus.EMPTY, "no documents to ground an answer on"),
            }
        try:
            answer = await answerer.generate(state.query, documents)
        except Exception as exc:  # noqa: BLE001 - LLM errors
            return _failure(ANSWER, exc)

        return {
            "final_answer": answer,
            "sources": _build_sources(documents),
            "stages": _stage(ANSWER, StageStatus.OK, f"grounded on {len(documents)} document(s)"),
        }

    return answer_node
