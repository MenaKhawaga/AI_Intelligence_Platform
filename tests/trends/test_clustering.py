from app.collectors.base import CollectedItem
from app.processing.normalization import ProcessedItem
from app.trends.clustering import cluster_items, similarity


def make_item(title, category="LLMs", entity="OpenAI", source="rss"):
    return ProcessedItem(
        **CollectedItem(
            source_type=source,
            source=source,
            title=title,
            url=f"https://example.com/{len(title)}-{entity}-{source}",
        ).model_dump(),
        categories=[category],
        primary_category=category,
        entities={"companies": [entity]},
    )


def test_related_items_cluster_together():
    items = [
        make_item("OpenAI launches new model"),
        make_item("OpenAI releases model update"),
        make_item("Robotics warehouse automation", category="Robotics", entity="Nvidia", source="github"),
    ]
    clusters = cluster_items(items, similarity_threshold=0.20)

    assert len(clusters) == 2
    assert sorted(len(c.items) for c in clusters) == [1, 2]


def test_similarity_is_bounded():
    left = make_item("OpenAI model release")
    right = make_item("OpenAI model update")
    assert 0.0 <= similarity(left, right) <= 1.0
