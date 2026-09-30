"""Phase 3 — Processing pipeline: classification.

Assigns each item one or more AI categories using keyword matching
against ``DEFAULT_CATEGORY_KEYWORDS`` below. Keyword-based classification
is intentionally simple and fully explainable (you can point at exactly
which words in the text triggered a category), and the category list is
just a dict -- easy to extend/edit later without touching this module's
logic.

Runs after filtering (filtering.py), so every item classified here has
already been confirmed AI-related; classification is about *which kind*
of AI content it is, not *whether* it's AI content.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Set

from app.processing.normalization import ProcessedItem

logger = logging.getLogger(__name__)

# Category -> keywords that indicate it. Order matters as a tie-breaker
# for `primary_category` (earlier category wins a tie in match count) --
# roughly broad-to-specific.
DEFAULT_CATEGORY_KEYWORDS: Dict[str, Set[str]] = {
    "LLMs": {
        "llm",
        "large language model",
        "gpt",
        "chatgpt",
        "claude",
        "gemini",
        "llama",
        "mistral",
        "chatbot",
        "prompt engineering",
        "context window",
        "fine-tuning",
        "fine tuning",
    },
    "Generative AI": {
        "generative ai",
        "genai",
        "text-to-image",
        "text-to-video",
        "diffusion model",
        "stable diffusion",
        "midjourney",
        "dall-e",
        "image generation",
        "video generation",
        "synthetic media",
    },
    "Computer Vision": {
        "computer vision",
        "image recognition",
        "object detection",
        "image segmentation",
        "facial recognition",
        "ocr",
        "cv model",
    },
    "NLP": {
        "nlp",
        "natural language processing",
        "text classification",
        "sentiment analysis",
        "named entity recognition",
        "language model",
        "tokenizer",
        "machine translation",
    },
    "Robotics": {
        "robot",
        "robotics",
        "humanoid",
        "autonomous vehicle",
        "self-driving",
        "drone",
        "manipulator arm",
    },
    "AI Agents": {
        "ai agent",
        "autonomous agent",
        "agentic",
        "multi-agent",
        "tool use",
        "agent framework",
        "orchestration",
    },
    "AI Research": {
        "arxiv",
        "paper",
        "research",
        "benchmark",
        "study",
        "dataset",
        "preprint",
        "reinforcement learning",
    },
    "AI Tools": {
        "sdk",
        "api",
        "library",
        "framework",
        "plugin",
        "extension",
        "developer tool",
        "cli",
    },
    "Open Source AI": {
        "open source",
        "open-source",
        "github repo",
        "apache license",
        "mit license",
        "open weights",
        "huggingface",
        "hugging face",
    },
    "AI/ML": {
        "artificial intelligence",
        "machine learning",
        "deep learning",
        "neural network",
        "neural net",
        "ai model",
        "foundation model",
        " ai ",
    },
}

# Fallback when nothing more specific matches -- everything reaching this
# stage already passed the filtering AI-relevance check, so it belongs
# *somewhere*.
FALLBACK_CATEGORY = "AI/ML"


def _searchable_text(item: ProcessedItem) -> str:
    return f" {item.title} {item.summary} {item.raw_text} ".lower()


def classify_item(
    item: ProcessedItem,
    category_keywords: Dict[str, Set[str]] = DEFAULT_CATEGORY_KEYWORDS,
) -> ProcessedItem:
    """Assign ``categories`` and ``primary_category`` to one item."""

    text = _searchable_text(item)
    match_counts: Dict[str, int] = {}
    for category, keywords in category_keywords.items():
        count = sum(1 for keyword in keywords if keyword in text)
        if count:
            match_counts[category] = count

    if not match_counts:
        item.categories = [FALLBACK_CATEGORY]
        item.primary_category = FALLBACK_CATEGORY
        return item

    # Sort by match count desc; dict insertion order (category_keywords'
    # order) breaks ties, since Python's sort is stable.
    ranked = sorted(match_counts, key=lambda cat: match_counts[cat], reverse=True)
    item.categories = ranked
    item.primary_category = ranked[0]
    return item


def classify_items(
    items: List[ProcessedItem],
    category_keywords: Dict[str, Set[str]] = DEFAULT_CATEGORY_KEYWORDS,
) -> List[ProcessedItem]:
    """Classify a batch of items into AI categories. Stage 5 of the pipeline."""

    for item in items:
        classify_item(item, category_keywords)
    logger.info("Classified %d item(s)", len(items))
    return items
