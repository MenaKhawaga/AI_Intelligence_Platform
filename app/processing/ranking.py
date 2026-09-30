"""Phase 3 — Processing pipeline: ranking.

Produces a single, explainable ``relevance_score`` (0-100) per item from
four signals, each normalized to 0-1 and then combined with a weight:

    relevance_score = 100 * (
        w_source     * source_quality
      + w_engagement * engagement
      + w_recency    * recency
      + w_relevance  * ai_relevance
    )

Every component and its weighted contribution is recorded on
``item.score_breakdown`` so the final number is always auditable --
nothing here is a black box. This is the last stage of the pipeline;
its output is sorted by ``relevance_score`` descending.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.processing.normalization import ProcessedItem

logger = logging.getLogger(__name__)


@dataclass
class RankingWeights:
    """How much each signal contributes to the final score. Must sum to 1.0."""

    source_quality: float = 0.25
    engagement: float = 0.30
    recency: float = 0.25
    ai_relevance: float = 0.20


DEFAULT_WEIGHTS = RankingWeights()

# How much to trust each source type's editorial/technical quality,
# independent of any one item's engagement numbers. arXiv is peer-adjacent
# research output; social sources (Reddit/HN) are community-voted and
# noisier.
DEFAULT_SOURCE_QUALITY: Dict[str, float] = {
    "arxiv": 1.0,
    "github": 0.85,
    "rss": 0.75,
    "hackernews": 0.70,
    "reddit": 0.55,
}
DEFAULT_SOURCE_QUALITY_FALLBACK = 0.6

# Rough "this is a big number for this source" cap used to normalize the
# native `score` field (points/stars/upvotes) onto 0-1 via a log curve, so
# one viral outlier doesn't blow the scale for everything else from that
# source. Sources with no native engagement metric (e.g. arXiv listings)
# are intentionally absent -- they use the neutral default instead.
DEFAULT_ENGAGEMENT_CAPS: Dict[str, float] = {
    "github": 5000.0,  # stars
    "hackernews": 500.0,  # points
    "reddit": 2000.0,  # upvotes
}
DEFAULT_ENGAGEMENT_CAP_FALLBACK = 1000.0
NEUTRAL_ENGAGEMENT = 0.5  # used when a source has no native score at all

# Recency half-life: an item this many days old scores 0.5 on recency.
RECENCY_HALF_LIFE_DAYS = 3.0
NEUTRAL_RECENCY = 0.5  # used when published_at is unknown


def source_quality_score(item: ProcessedItem, table: Dict[str, float] = DEFAULT_SOURCE_QUALITY) -> float:
    return table.get(item.source_type, DEFAULT_SOURCE_QUALITY_FALLBACK)


def engagement_score(
    item: ProcessedItem,
    caps: Dict[str, float] = DEFAULT_ENGAGEMENT_CAPS,
) -> float:
    """Log-scaled native engagement (points/stars/upvotes), normalized to 0-1."""

    if item.source_type not in caps or item.score <= 0:
        return NEUTRAL_ENGAGEMENT
    cap = caps[item.source_type]
    normalized = math.log1p(item.score) / math.log1p(cap)
    return max(0.0, min(1.0, normalized))


def recency_score(
    item: ProcessedItem,
    now: Optional[datetime] = None,
    half_life_days: float = RECENCY_HALF_LIFE_DAYS,
) -> float:
    """Exponential decay: freshly published = 1.0, halves every ``half_life_days``."""

    reference = item.published_at or item.collected_at
    if reference is None:
        return NEUTRAL_RECENCY

    now = now or datetime.now(timezone.utc)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=timezone.utc)

    age_days = max(0.0, (now - reference).total_seconds() / 86400.0)
    return 0.5 ** (age_days / half_life_days)


def ai_relevance_score(item: ProcessedItem) -> float:
    """How strongly this item matches AI topics/entities, from earlier stages.

    Built from classification.py's category matches and entities.py's
    entity hits rather than re-scanning text -- ranking trusts and
    combines the upstream stages' output instead of duplicating their
    work.
    """

    category_hits = len(item.categories)
    entity_hits = sum(len(v) for v in item.entities.values())
    # A specific (non-fallback) primary category is a stronger signal than
    # only matching the generic "AI/ML" bucket.
    specific_primary = 1 if item.primary_category not in (None, "AI/ML") else 0

    raw = 0.5 + 0.15 * specific_primary + 0.05 * min(category_hits, 4) + 0.03 * min(entity_hits, 5)
    return max(0.0, min(1.0, raw))


def score_item(
    item: ProcessedItem,
    weights: RankingWeights = DEFAULT_WEIGHTS,
    source_quality_table: Dict[str, float] = DEFAULT_SOURCE_QUALITY,
    engagement_caps: Dict[str, float] = DEFAULT_ENGAGEMENT_CAPS,
    now: Optional[datetime] = None,
) -> ProcessedItem:
    """Compute and set ``relevance_score``/``score_breakdown`` on one item."""

    components = {
        "source_quality": source_quality_score(item, source_quality_table),
        "engagement": engagement_score(item, engagement_caps),
        "recency": recency_score(item, now),
        "ai_relevance": ai_relevance_score(item),
    }
    weight_map = {
        "source_quality": weights.source_quality,
        "engagement": weights.engagement,
        "recency": weights.recency,
        "ai_relevance": weights.ai_relevance,
    }

    breakdown: Dict[str, float] = {}
    total = 0.0
    for name, value in components.items():
        weight = weight_map[name]
        contribution = value * weight
        breakdown[f"{name}_raw"] = round(value, 4)
        breakdown[f"{name}_weighted"] = round(contribution, 4)
        total += contribution

    item.score_breakdown = breakdown
    item.relevance_score = round(total * 100, 2)
    return item


def rank_items(
    items: List[ProcessedItem],
    weights: RankingWeights = DEFAULT_WEIGHTS,
    source_quality_table: Dict[str, float] = DEFAULT_SOURCE_QUALITY,
    engagement_caps: Dict[str, float] = DEFAULT_ENGAGEMENT_CAPS,
    now: Optional[datetime] = None,
) -> List[ProcessedItem]:
    """Score every item and return them sorted by relevance, highest first.

    Stage 7 (final stage) of the pipeline.
    """

    for item in items:
        score_item(item, weights, source_quality_table, engagement_caps, now)

    ranked = sorted(items, key=lambda i: i.relevance_score, reverse=True)
    logger.info("Ranked %d item(s)", len(ranked))
    return ranked
