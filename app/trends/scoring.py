"""Phase 7 — Trend scoring.

Combines volume, velocity, and source diversity into an explainable
0..100 trend strength. Each component is normalized independently.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log1p

from app.trends.signals import TrendSignal


@dataclass(frozen=True)
class TrendScore:
    """A scored trend with component values retained for explainability."""

    strength: float
    volume_score: float
    velocity_score: float
    diversity_score: float


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def score_signal(signal: TrendSignal) -> TrendScore:
    """Score one signal set on a bounded 0..100 scale."""

    volume_score = _clamp(log1p(signal.volume) / log1p(20) * 100.0)
    velocity_score = _clamp(signal.velocity / 4.0 * 100.0)
    diversity_score = _clamp(signal.source_diversity * 100.0)

    # Velocity is the primary "trending" signal; volume and independent
    # sources keep a short-lived single-source spike from dominating.
    strength = (
        0.45 * velocity_score
        + 0.35 * volume_score
        + 0.20 * diversity_score
    )
    return TrendScore(
        strength=round(strength, 2),
        volume_score=round(volume_score, 2),
        velocity_score=round(velocity_score, 2),
        diversity_score=round(diversity_score, 2),
    )
