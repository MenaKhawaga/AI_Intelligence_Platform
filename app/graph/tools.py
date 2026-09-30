"""Phase 6 — Graph: tools.

Only what the two graphs genuinely need beyond calling existing modules
directly. ``collect`` / ``process`` / ``summarize`` need no tool -- nodes
call ``BaseCollector.collect()``, ``process_items`` and ``summarize_items``
themselves. What is left falls in two groups.

Capabilities with no existing home (Phase 9's service layer does not exist
yet, and Phase 5's repositories deliberately know nothing about pipeline
models):

- ``default_collectors``  -- the standard set of source collectors.
- ``persist_results``     -- maps ``ProcessedItem`` / ``ArticleSummary`` onto
                             the Phase 5 repository functions.
- ``LLMAnswerGenerator``  -- the default grounded-answer step, on top of the
                             Phase 4 ``LLMService``.

Integration points for later phases (interfaces only, no implementation):

- ``Retriever`` / ``Reranker`` -- Phase 8 (RAG) plugs in here.
- ``PipelineHook``             -- Phase 7 (trends) and Phase 8 (indexing)
                                  plug in here.

All interfaces are ``Protocol``s, so a later phase satisfies them just by
having a matching method -- it does not need to import from this module.
Everything is async, consistent with collectors and ``LLMService``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Awaitable, Callable, ContextManager, List, Optional, Protocol, Sequence

from sqlalchemy.orm import Session

from app.collectors.base import BaseCollector
from app.database.repositories import create_source, save_summary, upsert_article
from app.database.session import get_session
from app.graph.state import RetrievedDocument
from app.processing.normalization import ProcessedItem
from app.services.llm_service import LLMService, get_llm_service
from app.summarization.structured_output import ArticleSummary

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Research side
# ---------------------------------------------------------------------------

#: A zero-argument callable returning a context manager that yields a
#: ``Session`` and commits/rolls back on exit -- exactly what
#: ``app.database.session.get_session`` is. Injectable so tests can point
#: the graph at an in-memory database.
SessionScope = Callable[[], ContextManager[Session]]

#: Optional post-persist step: receives the ranked items and their
#: summaries. Used for the trends (Phase 7) and indexing (Phase 8)
#: integration points. Returns nothing; anything it produces it stores
#: itself.
PipelineHook = Callable[[List[ProcessedItem], List[ArticleSummary]], Awaitable[None]]


def default_collectors() -> List[BaseCollector]:
    """The standard collectors: RSS, GitHub, Hacker News, arXiv, Reddit.

    Imported inside the function so importing the graph package does not
    pull in every collector's third-party dependency (praw, feedparser,
    ...) until a research graph is actually built with the defaults.
    """

    from app.collectors.arxiv import ArxivCollector
    from app.collectors.github import GitHubCollector
    from app.collectors.hackernews import HackerNewsCollector
    from app.collectors.reddit import RedditCollector
    from app.collectors.rss import RSSCollector

    return [
        RSSCollector(),
        GitHubCollector(),
        HackerNewsCollector(),
        ArxivCollector(),
        RedditCollector(),
    ]


@dataclass
class PersistResult:
    articles: int = 0
    summaries: int = 0
    article_ids: dict[str, int] = field(default_factory=dict)


def persist_results(
    items: Sequence[ProcessedItem],
    summaries: Sequence[ArticleSummary],
    session_scope: SessionScope = get_session,
) -> PersistResult:
    """Store ranked items and their summaries via the Phase 5 repositories.

    Runs in a single ``session_scope()`` block, so the whole batch commits
    or rolls back together. Both writes are upserts (keyed on the canonical
    URL / one summary per article), so re-running the pipeline over the
    same stories updates rows instead of duplicating them.

    Summaries are matched to articles by ``source_url``; a summary whose
    article is not in ``items`` is skipped (logged) rather than raising.
    """

 
    result = PersistResult()
    with session_scope() as session:
        article_ids = {}

        for item in items:
            # Create/update the canonical source record
            source_type = item.source_type.lower()
            source_name = item.source
            source_url = ""

            if source_type == "rss":
                source_url = item.metadata.get("feed_url", "")
                source_name = item.source or "RSS Feed"

            elif source_type == "github":
                source_name = "GitHub"
                source_url = "https://github.com/trending"

            elif source_type == "arxiv":
                source_name = "arXiv"
                source_url = "https://arxiv.org/"

            elif source_type == "hackernews":
                source_name = "Hacker News"
                source_url = "https://news.ycombinator.com/"

            elif source_type == "reddit":
                source_name = "Reddit"
                source_url = "https://www.reddit.com/"

            if source_name and source_url:
                create_source(
                    session,
                    name=source_name,
                    source_type=source_type,
                    url=source_url,
                    is_active=True,
                )

            article = upsert_article(
                session,
                url=item.url,
                source_type=item.source_type,
                source=item.source,
                title=item.title,
                snippet=item.summary,
                raw_text=item.raw_text,
                native_score=item.score,
                relevance_score=item.relevance_score,
                primary_category=item.primary_category,
                categories=item.categories,
                entities=item.entities,
                published_at=item.published_at,
                collected_at=item.collected_at,
                metadata=item.metadata,
            )
            article_ids[item.url] = article.id
            result.articles += 1

        for summary in summaries:
            article_id = article_ids.get(summary.source_url)
            if article_id is None:
                logger.warning("No stored article for summary of %r; skipping", summary.source_url)
                continue
            save_summary(
                session,
                article_id=article_id,
                headline=summary.headline,
                summary_text=summary.summary,
                why_it_matters=summary.why_it_matters,
                key_points=summary.key_points,
                generated_at=summary.generated_at,
            )
            result.summaries += 1

    result.article_ids = article_ids
    return result


# ---------------------------------------------------------------------------
# Chat side -- integration points for Phase 8 (RAG)
# ---------------------------------------------------------------------------


class Retriever(Protocol):
    """Finds knowledge relevant to a question. Implemented in Phase 8."""

    async def retrieve(self, query: str, top_k: int) -> List[RetrievedDocument]: ...


class Reranker(Protocol):
    """Reorders (and may trim) retrieved documents by relevance. Implemented in Phase 8."""

    async def rerank(self, query: str, documents: Sequence[RetrievedDocument]) -> List[RetrievedDocument]: ...


class AnswerGenerator(Protocol):
    """Produces an answer to ``query`` grounded in ``documents``."""

    async def generate(self, query: str, documents: Sequence[RetrievedDocument]) -> str: ...


ANSWER_SYSTEM_PROMPT = """You are the question-answering assistant of an AI intelligence platform.

Answer the user's QUESTION using ONLY the numbered SOURCES provided in the user message.

Rules:
- Base every statement strictly on the SOURCES. Do not use outside knowledge and do not \
invent numbers, quotes, dates, or details that are not present in them.
- If the SOURCES do not contain enough information to answer, say so plainly instead of guessing.
- Cite the sources you rely on inline as [1], [2], ... using the numbers given.
- Be concise and direct.
"""

# Keeps the prompt bounded regardless of how large a retrieved chunk is.
MAX_DOC_CHARS = 1500


def build_answer_prompt(query: str, documents: Sequence[RetrievedDocument]) -> str:
    """Build the user-turn prompt: the question plus numbered, truncated sources."""

    blocks = []
    for index, doc in enumerate(documents, start=1):
        content = doc.content
        if len(content) > MAX_DOC_CHARS:
            content = content[:MAX_DOC_CHARS].rstrip() + " [truncated]"
        header = f"[{index}] {doc.title or 'Untitled'}"
        if doc.source_url:
            header += f" ({doc.source_url})"
        blocks.append(f"{header}\n{content}")

    sources = "\n\n".join(blocks)
    return (
        f"QUESTION: {query}\n\n"
        f"SOURCES:\n{sources}\n\n"
        "Answer the QUESTION using only the SOURCES above."
    )


class LLMAnswerGenerator:
    """Default ``AnswerGenerator``: one grounded completion via ``LLMService``.

    The LLM is resolved lazily (``get_llm_service()`` on first use), so
    building a chat graph never needs an API key. Raises whatever the
    service raises (``LLMServiceError``); the answer node records it.
    """

    def __init__(self, llm: Optional[LLMService] = None) -> None:
        self._llm = llm

    async def generate(self, query: str, documents: Sequence[RetrievedDocument]) -> str:
        llm = self._llm or get_llm_service()
        return await llm.complete(system=ANSWER_SYSTEM_PROMPT, user=build_answer_prompt(query, documents))
