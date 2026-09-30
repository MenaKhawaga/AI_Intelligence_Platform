"""Phase 7 — Trend signals.

Computes explainable signals for a group of processed articles:
volume, recent velocity, and source diversity. No external services or
model calls are required.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional, Sequence

from app.processing.normalization import ProcessedItem


@dataclass(frozen=True)
class TrendSignal:
    """Raw, normalized inputs used by the trend scorer."""

    volume: int
    velocity: float
    source_diversity: float
    recent_volume: int
    baseline_volume: int


def _utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _item_time(item: ProcessedItem) -> Optional[datetime]:
    return _utc(item.published_at) or _utc(item.collected_at)


def compute_signals(
    items: Sequence[ProcessedItem],
    *,
    now: Optional[datetime] = None,
    recent_hours: float = 24.0,
    baseline_hours: float = 168.0,
) -> TrendSignal:
    """Compute volume, recent velocity, and source diversity.

    ``velocity`` is recent article rate divided by the average hourly rate
    in the preceding baseline window. A value above 1 means activity is
    increasing relative to that baseline; a value below 1 means it is
    decreasing. The baseline uses a full window and therefore remains
    deterministic for a fixed ``now``.
    """

    if recent_hours <= 0 or baseline_hours <= 0:
        raise ValueError("recent_hours and baseline_hours must be positive")

    current = _utc(now) or datetime.now(timezone.utc)
    recent_cutoff = current - timedelta(hours=recent_hours)
    baseline_cutoff = current - timedelta(hours=recent_hours + baseline_hours)

    dated = [(item, _item_time(item)) for item in items]
    recent = [item for item, stamp in dated if stamp is not None and stamp >= recent_cutoff]
    baseline = [
        item for item, stamp in dated
        if stamp is not None and baseline_cutoff <= stamp < recent_cutoff
    ]

    # Recent rate / historical rate. With no baseline, use a conservative
    # one-event baseline so a small burst does not become infinite.
    recent_rate = len(recent) / recent_hours
    baseline_rate = len(baseline) / baseline_hours
    velocity = recent_rate / max(baseline_rate, 1.0 / baseline_hours)

    sources = {item.source_type or item.source for item in items if (item.source_type or item.source)}
    source_diversity = len(sources) / max(len(items), 1)

    return TrendSignal(
        volume=len(items),
        velocity=velocity,
        source_diversity=source_diversity,
        recent_volume=len(recent),
        baseline_volume=len(baseline),
    )
