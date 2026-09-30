import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_high_relevance_article_alert(
    *,
    article_id: int,
    title: str,
    source: str,
    relevance_score: float,
    url: str,
    summary: str,
) -> bool:

    webhook_url = settings.N8N_HIGH_RELEVANCE_WEBHOOK_URL

    if not webhook_url:
        logger.warning("n8n high-relevance webhook URL is not configured")
        return False

    # Backend filter
    if relevance_score <= 0.8:
        return False

    payload = {
        "article_id": article_id,
        "title": title,
        "source": source,
        "relevance_score": relevance_score,
        "url": url,
        "summary": summary,
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT_SECONDS
        ) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()

        logger.info("High-relevance article sent to n8n: %s", title)
        return True

    except httpx.HTTPError as exc:
        logger.error("Failed to send article to n8n: %s", exc)
        return False


async def send_critical_trend_alert(
    *,
    topic_id: int,
    topic_label: str,
    score: float,
    velocity: str,
    article_count: int,
) -> bool:

    webhook_url = settings.N8N_TREND_ESCALATION_WEBHOOK_URL

    if not webhook_url:
        logger.warning("n8n trend-escalation webhook URL is not configured")
        return False

    # Backend filter
    if score <= 85:
        return False

    payload = {
        "topic_id": topic_id,
        "topic_label": topic_label,
        "score": score,
        "velocity": velocity,
        "article_count": article_count,
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT_SECONDS
        ) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()

        logger.info("Critical trend sent to n8n: %s", topic_label)
        return True

    except httpx.HTTPError as exc:
        logger.error("Failed to send critical trend to n8n: %s", exc)
        return False