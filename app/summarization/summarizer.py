"""Summarization service.

Converts processed intelligence items into structured article summaries
using the configured LLM provider.

The summarizer is intentionally fault tolerant:
- One failed article does not stop the batch.
- LLM errors are converted into SummarizationResult.error.
- The number of summaries can be limited to control API usage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from app.collectors.base import async_retry
from app.processing.normalization import ProcessedItem
from app.services.llm_service import (
    LLMService,
    LLMServiceError,
    get_llm_service,
)
from app.summarization.prompts import SYSTEM_PROMPT, build_user_prompt
from app.summarization.structured_output import (
    ArticleSummary,
    SummaryParseError,
    build_article_summary,
    parse_llm_json,
)

logger = logging.getLogger(__name__)


# Groq's free/on-demand limits can be reached quickly when a whole
# intelligence batch is summarized.
#
# The research pipeline may collect dozens of items, but summarizing
# every single item is unnecessary for the dashboard.
DEFAULT_SUMMARY_LIMIT = 6


@dataclass
class SummarizationResult:
    """Result of summarizing one item."""

    item: ProcessedItem
    summary: Optional[ArticleSummary] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.summary is not None


@async_retry(
    max_retries=2,
    backoff_factor=2.0,
    initial_delay=2.0,
)
async def _complete(
    llm: LLMService,
    system: str,
    user: str,
) -> str:
    """Execute an LLM request with controlled retries."""

    return await llm.complete(
        system=system,
        user=user,
        temperature=0.2,
        max_tokens=700,
    )


async def summarize_item(
    item: ProcessedItem,
    llm: Optional[LLMService] = None,
) -> SummarizationResult:
    """Summarize one processed item without raising."""

    try:
        llm = llm or get_llm_service()

        user_prompt = build_user_prompt(item)

        raw_response = await _complete(
            llm,
            SYSTEM_PROMPT,
            user_prompt,
        )

    except LLMServiceError as exc:
        logger.warning(
            "Summarization LLM call failed for %r: %s",
            item.url,
            exc,
        )

        return SummarizationResult(
            item=item,
            error=str(exc),
        )

    except Exception as exc:
        logger.exception(
            "Unexpected error summarizing %r",
            item.url,
        )

        return SummarizationResult(
            item=item,
            error=str(exc),
        )

    try:
        llm_fields = parse_llm_json(raw_response)

    except SummaryParseError as exc:
        logger.warning(
            "Could not parse LLM response for %r: %s",
            item.url,
            exc,
        )

        return SummarizationResult(
            item=item,
            error=str(exc),
        )

    try:
        summary = build_article_summary(
            item,
            llm_fields,
        )

    except Exception as exc:
        logger.exception(
            "Failed to build article summary for %r",
            item.url,
        )

        return SummarizationResult(
            item=item,
            error=str(exc),
        )

    return SummarizationResult(
        item=item,
        summary=summary,
    )


async def summarize_items(
    items: List[ProcessedItem],
    llm: Optional[LLMService] = None,
    limit: Optional[int] = None,
) -> List[SummarizationResult]:
    """Summarize a ranked batch of items.

    The input is already ranked by relevance. By default only the top
    DEFAULT_SUMMARY_LIMIT items are sent to the LLM. This prevents the
    scheduler from exhausting Groq's token-per-minute limit.

    Passing an explicit ``limit`` overrides the default.
    Passing ``limit=0`` returns an empty result list.
    """

    if not items:
        logger.info("No items to summarize.")
        return []

    llm = llm or get_llm_service()

    # Explicit limit wins.
    if limit is None:
        effective_limit = DEFAULT_SUMMARY_LIMIT
    else:
        effective_limit = max(0, limit)

    selected = items[:effective_limit]

    logger.info(
        "Starting summarization: %d selected from %d processed item(s)",
        len(selected),
        len(items),
    )

    results: List[SummarizationResult] = []

    for index, item in enumerate(selected, start=1):
        logger.debug(
            "Summarizing item %d/%d: %s",
            index,
            len(selected),
            item.url,
        )

        result = await summarize_item(
            item,
            llm=llm,
        )

        results.append(result)

    succeeded = sum(
        1
        for result in results
        if result.ok
    )

    failed = len(results) - succeeded

    logger.info(
        "Summarization finished: %d/%d successful, %d failed",
        succeeded,
        len(results),
        failed,
    )

    return results