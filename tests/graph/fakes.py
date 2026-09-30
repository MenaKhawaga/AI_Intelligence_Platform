"""Fakes and builders shared by tests/graph/.

Nothing here touches the network, a real LLM, or a real vector store:
collectors return canned items, the LLM returns canned JSON/text, and the
Phase 8 integration points (retriever/reranker/answerer) are recording
stand-ins.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable, List, Optional, Sequence

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel

from app.collectors.base import BaseCollector, CollectedItem
from app.graph.state import RetrievedDocument
from app.services.llm_service import LLMService, LLMServiceError

SUMMARY_JSON = """{
  "headline": "A headline",
  "summary": "A two sentence summary. It is grounded in the article.",
  "key_points": ["Point one", "Point two"],
  "why_it_matters": "It matters."
}"""


# --- collected data ---------------------------------------------------------


def collected(**overrides) -> CollectedItem:
    defaults = dict(
        source_type="hackernews",
        source="Hacker News (AI)",
        title="OpenAI releases GPT-4o model",
        url="https://example.com/openai-gpt4o",
        summary="OpenAI announced GPT-4o today.",
        score=250,
        published_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return CollectedItem(**defaults)


def two_ai_items() -> List[CollectedItem]:
    """Two distinct AI stories that survive the real processing pipeline."""

    return [
        collected(),
        collected(
            source_type="rss",
            source="TechCrunch",
            title="Anthropic launches new Claude model for enterprises",
            url="https://example.com/anthropic-claude",
            summary="Anthropic announced a new Claude LLM release.",
            score=40,
        ),
    ]


def off_topic_item() -> CollectedItem:
    """Dropped by the real filtering stage."""

    return collected(
        source_type="reddit",
        source="r/pics",
        title="My cat sleeping in a box",
        url="https://example.com/cat",
        summary="cute cat",
        score=500,
    )


# --- collectors -------------------------------------------------------------


class FakeCollector(BaseCollector):
    def __init__(self, source_type: str, items: Sequence[CollectedItem]) -> None:
        self.source_type = source_type
        self._items = list(items)

    async def _fetch(self) -> List[CollectedItem]:
        return list(self._items)


class RaisingCollector(BaseCollector):
    """A custom collector that breaks the 'collect() never raises' contract."""

    source_type = "broken"

    async def _fetch(self) -> List[CollectedItem]:  # pragma: no cover - never reached
        return []

    async def collect(self) -> List[CollectedItem]:
        raise RuntimeError("boom")


# --- LLM ---------------------------------------------------------------------


class FakeLLM(LLMService):
    """Returns ``SUMMARY_JSON`` unless a prompt contains one of ``fail_on``."""

    def __init__(self, response: str = SUMMARY_JSON, fail_on: Sequence[str] = ()) -> None:
        self.response = response
        self.fail_on = list(fail_on)
        self.calls: List[dict] = []

    async def complete(self, *, system: str, user: str, temperature: float = 0.2, max_tokens: int = 700) -> str:
        self.calls.append({"system": system, "user": user})
        if any(marker in user for marker in self.fail_on):
            raise LLMServiceError("simulated LLM failure")
        return self.response


# --- Phase 8 integration points ------------------------------------------------


def doc(n: int = 1, **overrides) -> RetrievedDocument:
    defaults = dict(
        content=f"Content of document {n}.",
        title=f"Doc {n}",
        source_url=f"https://example.com/doc{n}",
        score=1.0 / n,
    )
    defaults.update(overrides)
    return RetrievedDocument(**defaults)


class FakeRetriever:
    def __init__(self, documents: Optional[Sequence[RetrievedDocument]] = None, error: Optional[Exception] = None):
        self.documents = list(documents or [])
        self.error = error
        self.calls: List[tuple] = []

    async def retrieve(self, query: str, top_k: int) -> List[RetrievedDocument]:
        self.calls.append((query, top_k))
        if self.error:
            raise self.error
        return list(self.documents)


class FakeReranker:
    """Reverses the documents (an easy-to-assert reordering)."""

    def __init__(self, error: Optional[Exception] = None):
        self.error = error
        self.calls: List[tuple] = []

    async def rerank(self, query: str, documents: Sequence[RetrievedDocument]) -> List[RetrievedDocument]:
        self.calls.append((query, list(documents)))
        if self.error:
            raise self.error
        return list(reversed(documents))


class FakeAnswerer:
    def __init__(self, text: str = "The answer [1].", error: Optional[Exception] = None):
        self.text = text
        self.error = error
        self.calls: List[tuple] = []

    async def generate(self, query: str, documents: Sequence[RetrievedDocument]) -> str:
        self.calls.append((query, list(documents)))
        if self.error:
            raise self.error
        return self.text


# --- Agent chat model --------------------------------------------------------


class FakeToolCallingChatModel(GenericFakeChatModel):
    """``GenericFakeChatModel`` that also survives ``.bind_tools(...)``.

    ``build_agent_graph`` always calls ``model.bind_tools(selected_tools)``
    -- that's the real, production tool-calling contract it needs against a
    live ``ChatOpenAI``, and it must not be weakened just to make tests
    pass. ``GenericFakeChatModel`` (and ``BaseChatModel`` in general) has no
    default ``bind_tools`` implementation, since binding a tool schema is
    provider-specific; only concrete integrations like ``ChatOpenAI``
    implement it. This fake supplies a no-op override -- it ignores the
    tool schema and just returns itself, since it already knows which
    canned messages (including canned ``tool_calls``) to replay -- so agent
    tests can exercise the graph without a real LLM.
    """

    def bind_tools(self, tools, **kwargs):  # noqa: ANN001 - matches BaseChatModel signature
        return self


class RecordingHook:
    """A ``PipelineHook`` that records what it was called with."""

    def __init__(self, error: Optional[Exception] = None):
        self.error = error
        self.calls: List[tuple] = []

    async def __call__(self, items, summaries) -> None:
        self.calls.append((list(items), list(summaries)))
        if self.error:
            raise self.error
