"""Phase 3 — Processing pipeline.

Turns the raw ``List[CollectedItem]`` from app/collectors/ into a ranked
``List[ProcessedItem]``:

    Collected Items
    -> normalization   (normalization.py)
    -> cleaning        (cleaning.py)
    -> deduplication   (deduplication.py)
    -> filtering       (filtering.py)
    -> classification  (classification.py)
    -> entity extraction (entities.py)
    -> ranking         (ranking.py)

Each stage is independently usable (and independently tested, see
tests/processing/) -- ``process_items`` below is just the default
end-to-end wiring for the common case of running the whole pipeline.
"""

from __future__ import annotations

import logging
from typing import List

from app.collectors.base import CollectedItem
from app.processing.classification import DEFAULT_CATEGORY_KEYWORDS, classify_items
from app.processing.cleaning import clean_items
from app.processing.deduplication import deduplicate_items
from app.processing.entities import extract_entities
from app.processing.filtering import DEFAULT_FILTER_CONFIG, FilterConfig, filter_items
from app.processing.normalization import ProcessedItem, normalize_items
from app.processing.ranking import DEFAULT_WEIGHTS, RankingWeights, rank_items

logger = logging.getLogger(__name__)

__all__ = [
    "ProcessedItem",
    "FilterConfig",
    "RankingWeights",
    "process_items",
]


def process_items(
    items: List[CollectedItem],
    filter_config: FilterConfig = DEFAULT_FILTER_CONFIG,
    category_keywords: dict = DEFAULT_CATEGORY_KEYWORDS,
    ranking_weights: RankingWeights = DEFAULT_WEIGHTS,
) -> List[ProcessedItem]:
    """Run the full processing pipeline end-to-end.

    Takes the combined output of all collectors and returns a
    deduplicated, filtered, classified, entity-tagged list of
    ``ProcessedItem``, sorted by ``relevance_score`` descending.
    """

    logger.info("Processing pipeline starting with %d raw item(s)", len(items))

    normalized = normalize_items(items)
    cleaned = clean_items(normalized)
    deduplicated = deduplicate_items(cleaned)
    filtered = filter_items(deduplicated, filter_config)
    classified = classify_items(filtered, category_keywords)
    with_entities = extract_entities(classified)
    ranked = rank_items(with_entities, ranking_weights)

    logger.info(
        "Processing pipeline finished: %d raw -> %d processed item(s)",
        len(items),
        len(ranked),
    )
    return ranked
