"""Phase 5/12 — Scheduler

Defines the hourly (``settings.collection_interval_minutes``) background
collection job and the asyncio loop that runs it while
``settings.scheduler_enabled`` is true. Started/stopped from the FastAPI
app's lifespan (see ``app/api/app.py``) -- no extra process or dependency
needed, since Uvicorn already runs one asyncio event loop for the app.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings
from app.graph.factory import build_production_graph
from app.graph.research_graph import run_research
from app.scheduler.run_manager import run_manager

logger = logging.getLogger(__name__)

_task: Optional[asyncio.Task] = None


async def run_collection_job() -> None:
    """Run the research/intelligence pipeline once and record the outcome.

    Never raises -- a failed run (a dead source, a flaky LLM call, ...) is
    recorded on ``run_manager`` and logged; the next scheduled run still
    happens.
    """

    run_manager.start()
    try:
        graph = build_production_graph()
        state = await run_research(graph)
        run_manager.finish_ok(
            collected=len(state.collected_items),
            processed=len(state.processed_items),
            summaries=len(state.summaries),
            persisted_articles=state.persisted_articles,
        )
        logger.info(
            "Scheduled collection run complete: collected=%d processed=%d summaries=%d persisted=%d",
            len(state.collected_items),
            len(state.processed_items),
            len(state.summaries),
            state.persisted_articles,
        )
    except Exception as exc:  # noqa: BLE001 - the loop must survive any single bad run
        logger.exception("Scheduled collection run failed")
        run_manager.finish_failed(str(exc) or type(exc).__name__)


async def _loop() -> None:
    interval_seconds = max(1, settings.COLLECTION_INTERVAL_MINUTES) * 60
    while True:
        await run_collection_job()
        run_manager.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=interval_seconds)
        await asyncio.sleep(interval_seconds)


def start_scheduler() -> None:
    """Start the background collection loop if enabled and not already running.

    Runs one collection immediately on startup, then every
    ``collection_interval_minutes``. No-op if ``scheduler_enabled`` is
    false (the default) so tests and one-off runs are unaffected.
    """

    global _task
    if not settings.SCHEDULER_ENABLED:
        logger.info("Scheduler disabled (SCHEDULER_ENABLED=false) -- set it to true in .env to auto-collect news.")
        return
    if _task is not None and not _task.done():
        return
    _task = asyncio.create_task(_loop())
    logger.info("Scheduler started: collecting fresh intelligence every %d minute(s).", settings.COLLECTION_INTERVAL_MINUTES)


def stop_scheduler() -> None:
    global _task
    if _task is not None:
        _task.cancel()
        _task = None
