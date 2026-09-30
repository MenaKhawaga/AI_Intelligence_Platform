"""Phase 3 — Processing pipeline: entity extraction.

Deliberately lightweight: this is gazetteer matching (curated lists of
known companies/models/technologies/organizations/people, matched
case-insensitively with word boundaries), not statistical NER. That
keeps it fully explainable -- every entity found can be traced back to
exactly which known name matched -- and dependency-free, per the Phase 3
requirement to avoid an unnecessarily complicated NER system.

The gazetteers are intentionally editable module-level constants, not
hardcoded logic, so the list of tracked companies/models/etc. can grow
without touching the matching code.
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Set

from app.processing.normalization import ProcessedItem

logger = logging.getLogger(__name__)

COMPANIES: Set[str] = {
    "OpenAI", "Anthropic", "Google DeepMind", "DeepMind", "Google", "Microsoft",
    "Meta", "Meta AI", "Amazon", "AWS", "Apple", "Nvidia", "Mistral AI", "Mistral",
    "Cohere", "Hugging Face", "Stability AI", "Midjourney", "xAI", "Perplexity",
    "Databricks", "Scale AI", "Inflection AI", "Character.AI", "Runway",
    "ElevenLabs", "Groq", "SambaNova", "Together AI", "Adept",
}

MODELS: Set[str] = {
    "GPT-4", "GPT-4o", "GPT-5", "GPT-3.5", "ChatGPT", "Claude", "Claude Opus",
    "Claude Sonnet", "Claude Haiku", "Gemini", "Gemini Ultra", "Gemini Pro",
    "Llama", "Llama 3", "Llama 4", "Mistral Large", "Mixtral", "DeepSeek",
    "DeepSeek-R1", "Grok", "Command R", "Stable Diffusion", "DALL-E", "Sora",
    "Whisper", "Midjourney", "Phi-3", "Qwen", "PaLM",
}

TECHNOLOGIES: Set[str] = {
    "transformer", "diffusion model", "reinforcement learning",
    "reinforcement learning from human feedback", "RLHF", "fine-tuning",
    "LoRA", "quantization", "RAG", "retrieval-augmented generation",
    "embedding", "vector database", "attention mechanism",
    "mixture of experts", "MoE", "prompt engineering", "tokenizer",
    "multimodal", "chain of thought", "agentic workflow", "knowledge graph",
}

ORGANIZATIONS: Set[str] = {
    "MIT", "Stanford", "UC Berkeley", "Berkeley", "Carnegie Mellon",
    "Oxford", "Cambridge", "arXiv", "NeurIPS", "ICML", "ICLR", "AAAI",
    "Allen Institute for AI", "AI2", "EleutherAI", "Linux Foundation",
    "Partnership on AI", "MLCommons",
}

PEOPLE: Set[str] = {
    "Sam Altman", "Dario Amodei", "Daniela Amodei", "Demis Hassabis",
    "Yann LeCun", "Geoffrey Hinton", "Andrew Ng", "Elon Musk",
    "Satya Nadella", "Sundar Pichai", "Mark Zuckerberg", "Ilya Sutskever",
    "Mira Murati", "Fei-Fei Li", "Jensen Huang", "Yoshua Bengio",
    "Greg Brockman", "Andrej Karpathy",
}

GAZETTEERS: Dict[str, Set[str]] = {
    "companies": COMPANIES,
    "models": MODELS,
    "technologies": TECHNOLOGIES,
    "organizations": ORGANIZATIONS,
    "people": PEOPLE,
}


def _compile_patterns(gazetteer: Set[str]) -> List[re.Pattern]:
    """One case-insensitive, word-boundary regex per gazetteer entry.

    ``re.escape`` keeps entries like "DALL-E" or "C++"-style names safe;
    word boundaries stop "AI2" from matching inside "SAI27", etc.
    """

    return [
        re.compile(rf"(?<![\w]){re.escape(name)}(?![\w])", re.IGNORECASE)
        for name in gazetteer
    ]


# Pre-compiled once at import time -- gazetteers are static, so there's no
# need to rebuild the regexes per item.
_COMPILED_GAZETTEERS: Dict[str, List[tuple[str, re.Pattern]]] = {
    label: list(zip(sorted(names), _compile_patterns(sorted(names))))
    for label, names in GAZETTEERS.items()
}


def extract_entities_from_text(text: str) -> Dict[str, List[str]]:
    """Find every gazetteer entry mentioned in ``text``, grouped by type."""

    found: Dict[str, List[str]] = {}
    for label, name_patterns in _COMPILED_GAZETTEERS.items():
        matches = [name for name, pattern in name_patterns if pattern.search(text)]
        if matches:
            found[label] = matches
    return found


def extract_entities_item(item: ProcessedItem) -> ProcessedItem:
    """Set ``entities`` on one item from its title/summary/raw_text."""

    text = f"{item.title} {item.summary} {item.raw_text}"
    item.entities = extract_entities_from_text(text)
    return item


def extract_entities(items: List[ProcessedItem]) -> List[ProcessedItem]:
    """Extract entities for a batch of items. Stage 6 of the pipeline."""

    for item in items:
        extract_entities_item(item)
    total = sum(len(i.entities) for i in items)
    logger.info("Extracted entities for %d item(s) (%d item-entity-types matched)", len(items), total)
    return items
