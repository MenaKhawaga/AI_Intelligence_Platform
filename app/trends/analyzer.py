"""Phase 7 — Trend analysis.

Clusters processed content, computes activity signals, and scores each
cluster into a stable, explainable trend result.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Sequence

from app.processing.normalization import ProcessedItem
from app.trends.clustering import TopicCluster, cluster_items
from app.trends.scoring import TrendScore, score_signal
from app.trends.signals import TrendSignal, compute_signals


@dataclass(frozen=True)
class Trend:
    """One detected topic with its evidence and score."""

    name: str
    description: str
    item_count: int
    source_count: int
    first_seen_at: Optional[datetime]
    last_seen_at: Optional[datetime]
    signal: TrendSignal
    score: TrendScore
    items: tuple[ProcessedItem, ...]


def _description(cluster: TopicCluster, signal: TrendSignal, score: TrendScore) -> str:
    return (
        f"{signal.volume} related item(s) across {len(cluster.source_types)} source(s); "
        f"recent activity={signal.recent_volume}, baseline activity={signal.baseline_volume}; "
        f"trend strength={score.strength}/100."
    )


def analyze_trends(
    items: Sequence[ProcessedItem],
    *,
    now: Optional[datetime] = None,
    recent_hours: float = 24.0,
    baseline_hours: float = 168.0,
    similarity_threshold: float = 0.30,
    min_cluster_size: int = 1,
) -> List[Trend]:
    """Return detected trends ordered by descending trend strength."""

    clusters = cluster_items(
        items,
        similarity_threshold=similarity_threshold,
        min_cluster_size=min_cluster_size,
    )
    trends: List[Trend] = []
    for cluster in clusters:
        signal = compute_signals(
            cluster.items,
            now=now,
            recent_hours=recent_hours,
            baseline_hours=baseline_hours,
        )
        score = score_signal(signal)
        trends.append(
            Trend(
                name=cluster.name,
                description=_description(cluster, signal, score),
                item_count=len(cluster.items),
                source_count=len(cluster.source_types),
                first_seen_at=cluster.first_seen_at,
                last_seen_at=cluster.last_seen_at,
                signal=signal,
                score=score,
                items=tuple(cluster.items),
            )
        )

    return sorted(trends, key=lambda trend: (-trend.score.strength, trend.name.lower()))
