from app.trends.scoring import score_signal
from app.trends.signals import TrendSignal


def test_score_is_bounded_and_explainable():
    score = score_signal(
        TrendSignal(
            volume=10,
            velocity=2.0,
            source_diversity=0.5,
            recent_volume=5,
            baseline_volume=3,
        )
    )
    assert 0.0 <= score.strength <= 100.0
    assert score.volume_score > 0
    assert score.velocity_score > 0
    assert score.diversity_score == 50.0
