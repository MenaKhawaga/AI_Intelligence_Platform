"""Phase 4 — Summarization: structured output schema.

Defines the structured shape a summary takes, and how a raw LLM text
response gets parsed and validated into it.

Anti-hallucination design note: only four fields are ever asked of the
LLM -- ``headline``, ``summary``, ``key_points``, ``why_it_matters`` (see
``LLMSummaryFields``). ``category``, ``entities`` and ``source_url`` are
*not* requested from the model at all; they are copied straight from the
already-verified ``ProcessedItem`` produced by Phase 3 (classification.py
/ entities.py / the collector's own URL), in ``build_article_summary``.
That removes any chance of the model inventing a category, an entity, or
-- worst of all -- a wrong source link, for the fields where a
deterministic answer already exists.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Dict, List

from pydantic import BaseModel, Field, ValidationError, field_validator

from app.processing.normalization import ProcessedItem


class SummaryParseError(Exception):
    """Raised when an LLM response can't be parsed into ``LLMSummaryFields``."""


class LLMSummaryFields(BaseModel):
    """The subset of the summary the LLM is actually asked to generate.

    Kept separate from ``ArticleSummary`` so it's obvious, just from the
    type, which fields come from the model and which come from Phase 3's
    deterministic output.
    """

    headline: str
    summary: str
    key_points: List[str] = Field(default_factory=list)
    why_it_matters: str

    @field_validator("headline", "summary", "why_it_matters")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("must not be blank")
        return value.strip()

    @field_validator("key_points")
    @classmethod
    def _clean_key_points(cls, value: List[str]) -> List[str]:
        cleaned = [p.strip() for p in value if isinstance(p, str) and p.strip()]
        if not cleaned:
            raise ValueError("key_points must contain at least one non-empty item")
        return cleaned


class ArticleSummary(BaseModel):
    """The full structured summary returned by the summarizer.

    ``headline`` / ``summary`` / ``key_points`` / ``why_it_matters`` come
    from the LLM (via ``LLMSummaryFields``). Everything else is carried
    over unchanged from the ``ProcessedItem`` that was summarized, so the
    original article/source information is never lost.
    """

    headline: str
    summary: str
    key_points: List[str]
    why_it_matters: str
    category: str
    entities: Dict[str, List[str]] = Field(default_factory=dict)
    source_url: str
    source_title: str = ""
    source: str = ""
    source_type: str = ""
    relevance_score: float = 0.0
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```\s*$", re.IGNORECASE | re.MULTILINE)


def _strip_code_fences(text: str) -> str:
    """Remove a ```json ... ``` wrapper some models add despite instructions not to."""

    text = text.strip()
    if text.startswith("```"):
        text = _CODE_FENCE_RE.sub("", text).strip()
    return text


def parse_llm_json(raw_text: str) -> LLMSummaryFields:
    """Parse+validate a raw LLM text response into ``LLMSummaryFields``.

    Raises ``SummaryParseError`` (never a bare pydantic/json exception)
    on anything that doesn't come back as a valid JSON object matching
    the expected shape, so callers have one exception type to handle.
    """

    if not raw_text or not raw_text.strip():
        raise SummaryParseError("Empty response from LLM")

    cleaned = _strip_code_fences(raw_text)

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SummaryParseError(f"LLM response was not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise SummaryParseError("LLM response JSON was not an object")

    try:
        return LLMSummaryFields(**data)
    except ValidationError as exc:
        raise SummaryParseError(f"LLM response JSON did not match the summary schema: {exc}") from exc


def build_article_summary(item: ProcessedItem, fields: LLMSummaryFields) -> ArticleSummary:
    """Merge the LLM-generated fields with the item's own verified data."""

    return ArticleSummary(
        headline=fields.headline,
        summary=fields.summary,
        key_points=fields.key_points,
        why_it_matters=fields.why_it_matters,
        category=item.primary_category or "AI/ML",
        entities=item.entities,
        source_url=item.url,
        source_title=item.title,
        source=item.source,
        source_type=item.source_type,
        relevance_score=item.relevance_score,
    )
