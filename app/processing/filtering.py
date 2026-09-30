"""Phase 3 — Processing pipeline: filtering.

Drops items that are irrelevant (not actually about AI) or low-quality,
using explicit, configurable rules rather than a model -- so the rules
stay inspectable and easy to tune as the platform's definition of
"relevant" changes.

Runs after deduplication (deduplication.py) and before classification
(classification.py): classification assumes everything it sees already
passed the "is this AI-related at all" bar set here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Set

from app.processing.normalization import ProcessedItem

logger = logging.getLogger(__name__)

# Broad AI-relevance vocabulary. An item needs at least one hit (in title,
# summary, or raw_text) to be considered AI-related at all. Deliberately
# broad/high-recall here -- classification.py does the fine-grained
# category assignment afterwards.
DEFAULT_AI_KEYWORDS: Set[str] = {
    "ai",
    "a.i.",
    "artificial intelligence",
    "machine learning",
    "ml",
    "deep learning",
    "neural network",
    "neural net",
    "llm",
    "large language model",
    "gpt",
    "chatgpt",
    "generative ai",
    "genai",
    "transformer",
    "diffusion model",
    "computer vision",
    "nlp",
    "natural language processing",
    "reinforcement learning",
    "ai agent",
    "ai model",
    "foundation model",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "llama",
    "mistral",
    "hugging face",
    "robotics",
    "autonomous agent",
}

# Content signalling low quality or off-topic despite an AI keyword hit
# (e.g. an AI-themed ad, a job posting, a giveaway).
DEFAULT_BLOCKED_KEYWORDS: Set[str] = {
    "sponsored post",
    "advertisement",
    "buy now",
    "% off",
    "discount code",
    "nsfw",
    "casino",
}

DEFAULT_MIN_TITLE_LENGTH = 8


@dataclass
class FilterConfig:
    """Tunable filtering rules. Pass a custom instance to change behavior
    without editing this module's logic."""

    ai_keywords: Set[str] = field(default_factory=lambda: set(DEFAULT_AI_KEYWORDS))
    blocked_keywords: Set[str] = field(default_factory=lambda: set(DEFAULT_BLOCKED_KEYWORDS))
    require_ai_keyword: bool = True
    min_title_length: int = DEFAULT_MIN_TITLE_LENGTH
    min_score: float = 0.0  # native engagement floor; 0.0 = no floor
    allowed_source_types: Optional[Set[str]] = None  # None = allow all


DEFAULT_FILTER_CONFIG = FilterConfig()


def _searchable_text(item: ProcessedItem) -> str:
    return f"{item.title} {item.summary} {item.raw_text}".lower()


def matches_ai_keyword(item: ProcessedItem, config: FilterConfig) -> bool:
    text = _searchable_text(item)
    return any(keyword in text for keyword in config.ai_keywords)


def matches_blocked_keyword(item: ProcessedItem, config: FilterConfig) -> bool:
    text = _searchable_text(item)
    return any(keyword in text for keyword in config.blocked_keywords)


def passes_filters(item: ProcessedItem, config: FilterConfig = DEFAULT_FILTER_CONFIG) -> bool:
    """Whether a single item should be kept, per ``config``'s rules."""

    if len(item.title) < config.min_title_length:
        return False
    if config.allowed_source_types is not None and item.source_type not in config.allowed_source_types:
        return False
    if item.score < config.min_score:
        return False
    if matches_blocked_keyword(item, config):
        return False
    if config.require_ai_keyword and not matches_ai_keyword(item, config):
        return False
    return True


def filter_items(
    items: List[ProcessedItem], config: FilterConfig = DEFAULT_FILTER_CONFIG
) -> List[ProcessedItem]:
    """Filter out irrelevant/low-quality items. Stage 4 of the pipeline."""

    kept = [item for item in items if passes_filters(item, config)]
    logger.info(
        "Filtered %d item(s) -> %d kept (%d dropped)",
        len(items),
        len(kept),
        len(items) - len(kept),
    )
    return kept
