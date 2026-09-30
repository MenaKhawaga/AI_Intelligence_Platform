"""Phase 5/12 — Scheduler

Tracks the status of scheduled pipeline runs (idle/running/ok/failed, last
run counts, next run time) so the API and frontend can show what the
background collector is doing without re-running the pipeline themselves.
Purely in-memory -- one process-wide instance, reset on restart.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class RunStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    OK = "ok"
    FAILED = "failed"


@dataclass
class RunRecord:
    status: RunStatus = RunStatus.IDLE
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    detail: str = ""
    collected: int = 0
    processed: int = 0
    summaries: int = 0
    persisted_articles: int = 0


class RunManager:
    """In-memory record of the scheduler's most recent run plus the next
    scheduled run time. Shared between ``jobs.py`` (writer) and any API
    route that wants to report scheduler status (reader)."""

    def __init__(self) -> None:
        self.last_run: RunRecord = RunRecord()
        self.next_run_at: Optional[datetime] = None
        self.run_count: int = 0

    def start(self) -> None:
        self.last_run = RunRecord(status=RunStatus.RUNNING, started_at=datetime.now(timezone.utc))

    def finish_ok(self, *, collected: int, processed: int, summaries: int, persisted_articles: int) -> None:
        self.last_run.status = RunStatus.OK
        self.last_run.finished_at = datetime.now(timezone.utc)
        self.last_run.collected = collected
        self.last_run.processed = processed
        self.last_run.summaries = summaries
        self.last_run.persisted_articles = persisted_articles
        self.run_count += 1

    def finish_failed(self, detail: str) -> None:
        self.last_run.status = RunStatus.FAILED
        self.last_run.finished_at = datetime.now(timezone.utc)
        self.last_run.detail = detail
        self.run_count += 1

    def snapshot(self) -> dict:
        return {
            "status": self.last_run.status.value,
            "started_at": self.last_run.started_at,
            "finished_at": self.last_run.finished_at,
            "detail": self.last_run.detail,
            "collected": self.last_run.collected,
            "processed": self.last_run.processed,
            "summaries": self.last_run.summaries,
            "persisted_articles": self.last_run.persisted_articles,
            "next_run_at": self.next_run_at,
            "run_count": self.run_count,
        }


#: Process-wide instance -- ``jobs.py`` writes to it, API routes read it.
run_manager = RunManager()
