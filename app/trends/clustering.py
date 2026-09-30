"""Phase 7 — Deterministic topic clustering.

Related articles are grouped using shared categories/entities and title
token overlap. This deliberately avoids an embedding/vector dependency;
Phase 8 owns RAG/indexing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, List, Sequence, Set

from app.processing.normalization import ProcessedItem

_TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9+#.-]{1,}")


@dataclass
class TopicCluster:
    """A group of related processed items."""

    name: str
    items: List[ProcessedItem] = field(default_factory=list)

    @property
    def source_types(self) -> Set[str]:
        return {i.source_type or i.source for i in self.items if i.source_type or i.source}

    @property
    def first_seen_at(self):
        values = [i.published_at or i.collected_at for i in self.items if i.published_at or i.collected_at]
        return min(values) if values else None

    @property
    def last_seen_at(self):
        values = [i.published_at or i.collected_at for i in self.items if i.published_at or i.collected_at]
        return max(values) if values else None


def _tokens(item: ProcessedItem) -> Set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(item.title) if len(t) >= 3}


def _features(item: ProcessedItem) -> Set[str]:
    features = {f"category:{c.lower()}" for c in item.categories}
    for kind, names in item.entities.items():
        features.update(f"entity:{kind}:{name.lower()}" for name in names)
    return features


def similarity(left: ProcessedItem, right: ProcessedItem) -> float:
    """Return a deterministic 0..1 relatedness score."""

    lt, rt = _tokens(left), _tokens(right)
    lf, rf = _features(left), _features(right)
    token_jaccard = len(lt & rt) / len(lt | rt) if lt | rt else 0.0
    feature_jaccard = len(lf & rf) / len(lf | rf) if lf | rf else 0.0
    return 0.65 * token_jaccard + 0.35 * feature_jaccard


def _cluster_name(items: Sequence[ProcessedItem]) -> str:
    # Prefer a shared entity; otherwise use the most common primary category;
    # finally use the first title as a stable human-readable fallback.
    entity_counts = {}
    for item in items:
        for names in item.entities.values():
            for name in names:
                entity_counts[name] = entity_counts.get(name, 0) + 1
    if entity_counts:
        return max(entity_counts, key=lambda name: (entity_counts[name], name.lower()))

    categories = [i.primary_category for i in items if i.primary_category]
    if categories:
        return max(set(categories), key=lambda name: (categories.count(name), name.lower()))

    return items[0].title[:255] if items else "Untitled topic"


def cluster_items(
    items: Sequence[ProcessedItem],
    *,
    similarity_threshold: float = 0.30,
    min_cluster_size: int = 1,
) -> List[TopicCluster]:
    """Group related items with single-link clustering.

    An item joins a cluster when it is sufficiently similar to at least one
    existing member. Results are ordered by cluster size, then name.
    """

    if not 0.0 <= similarity_threshold <= 1.0:
        raise ValueError("similarity_threshold must be between 0 and 1")
    if min_cluster_size < 1:
        raise ValueError("min_cluster_size must be at least 1")

    clusters: List[List[ProcessedItem]] = []
    for item in items:
        matches = [
            idx for idx, members in enumerate(clusters)
            if any(similarity(item, member) >= similarity_threshold for member in members)
        ]
        if not matches:
            clusters.append([item])
            continue
        first = matches[0]
        clusters[first].append(item)
        # Merge all additional matching clusters.
        for idx in reversed(matches[1:]):
            clusters[first].extend(clusters.pop(idx))

    result = [
        TopicCluster(name=_cluster_name(group), items=group)
        for group in clusters if len(group) >= min_cluster_size
    ]
    return sorted(result, key=lambda c: (-len(c.items), c.name.lower()))
