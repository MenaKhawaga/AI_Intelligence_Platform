"""Phase 7 trend detection public API."""

from app.trends.analyzer import Trend, analyze_trends
from app.trends.clustering import TopicCluster, cluster_items, similarity
from app.trends.scoring import TrendScore, score_signal
from app.trends.signals import TrendSignal, compute_signals

__all__ = [
    "Trend",
    "TrendSignal",
    "TrendScore",
    "TopicCluster",
    "analyze_trends",
    "compute_signals",
    "score_signal",
    "cluster_items",
    "similarity",
    "make_trends_hook",
]

from app.trends.hook import make_trends_hook
