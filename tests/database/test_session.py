from __future__ import annotations

from datetime import datetime, timezone

from app.database.repositories import (
    articles_for_entity,
    articles_for_topic,
    get_article_by_id,
    get_article_by_url,
    get_entity,
    get_or_create_topic,
    get_summary_by_article_id,
    get_topic,
    list_articles,
    list_entities,
    list_summaries,
    list_topics,
    save_summary,
    upsert_article,
)


def utcnow():
    return datetime.now(timezone.utc)


def test_upsert_article_creates_article(db_session):
    article = upsert_article(
        db_session,
        url="https://example.com/article-1",
        source_type="rss",
        source="Test Source",
        title="Test Article",
    )

    db_session.commit()

    assert article.id is not None

    saved = get_article_by_url(
        db_session,
        "https://example.com/article-1",
    )

    assert saved is not None
    assert saved.title == "Test Article"


def test_upsert_article_updates_existing_article(db_session):
    upsert_article(
        db_session,
        url="https://example.com/article-1",
        source_type="rss",
        source="Test Source",
        title="Old Title",
    )

    db_session.commit()

    updated = upsert_article(
        db_session,
        url="https://example.com/article-1",
        source_type="rss",
        source="Test Source",
        title="New Title",
    )

    db_session.commit()

    assert updated.title == "New Title"

    articles = list_articles(db_session)

    assert len(articles) == 1
    assert articles[0].title == "New Title"


def test_get_article_by_id(db_session):
    article = upsert_article(
        db_session,
        url="https://example.com/article-1",
        source_type="rss",
        source="Test Source",
        title="Test Article",
    )

    db_session.commit()

    result = get_article_by_id(
        db_session,
        article.id,
    )

    assert result is not None
    assert result.title == "Test Article"


def test_upsert_article_with_categories_and_entities(db_session):
    article = upsert_article(
        db_session,
        url="https://example.com/article-1",
        source_type="rss",
        source="Test Source",
        title="AI Article",
        categories=["LLMs", "AI"],
        entities={
            "company": ["OpenAI"],
            "model": ["GPT-5"],
        },
    )

    db_session.commit()

    saved = get_article_by_id(
        db_session,
        article.id,
    )

    assert saved is not None

    category_names = {category.name for category in saved.categories}

    assert category_names == {"LLMs", "AI"}

    entity_pairs = {
        (entity.name, entity.entity_type)
        for entity in saved.entities
    }

    assert entity_pairs == {
        ("OpenAI", "company"),
        ("GPT-5", "model"),
    }


def test_upsert_article_does_not_duplicate_categories_or_entities(db_session):
    upsert_article(
        db_session,
        url="https://example.com/article-1",
        source_type="rss",
        source="Test Source",
        title="Test Article",
        categories=["AI"],
        entities={"company": ["OpenAI"]},
    )

    db_session.commit()

    upsert_article(
        db_session,
        url="https://example.com/article-1",
        source_type="rss",
        source="Test Source",
        title="Updated Article",
        categories=["AI"],
        entities={"company": ["OpenAI"]},
    )

    db_session.commit()

    articles = list_articles(db_session)

    assert len(articles) == 1
    assert len(articles[0].categories) == 1
    assert len(articles[0].entities) == 1


def test_list_articles_by_source_type(db_session):
    upsert_article(
        db_session,
        url="https://example.com/rss",
        source_type="rss",
        source="RSS",
        title="RSS Article",
    )

    upsert_article(
        db_session,
        url="https://example.com/github",
        source_type="github",
        source="GitHub",
        title="GitHub Article",
    )

    db_session.commit()

    articles = list_articles(
        db_session,
        source_type="rss",
    )

    assert len(articles) == 1
    assert articles[0].title == "RSS Article"


def test_list_articles_by_category(db_session):
    upsert_article(
        db_session,
        url="https://example.com/ai",
        source_type="rss",
        source="RSS",
        title="AI Article",
        categories=["AI"],
    )

    upsert_article(
        db_session,
        url="https://example.com/robotics",
        source_type="rss",
        source="RSS",
        title="Robotics Article",
        categories=["Robotics"],
    )

    db_session.commit()

    articles = list_articles(
        db_session,
        category="AI",
    )

    assert len(articles) == 1
    assert articles[0].title == "AI Article"


def test_list_articles_limit_and_offset(db_session):
    for i in range(5):
        upsert_article(
            db_session,
            url=f"https://example.com/{i}",
            source_type="rss",
            source="RSS",
            title=f"Article {i}",
            relevance_score=float(i),
        )

    db_session.commit()

    articles = list_articles(
        db_session,
        limit=2,
        offset=1,
    )

    assert len(articles) == 2


def test_save_summary(db_session):
    article = upsert_article(
        db_session,
        url="https://example.com/article",
        source_type="rss",
        source="RSS",
        title="Test Article",
    )

    db_session.commit()

    summary = save_summary(
        db_session,
        article_id=article.id,
        headline="Test Headline",
        summary_text="Test Summary",
        why_it_matters="Important",
        key_points=["Point 1", "Point 2"],
        generated_at=utcnow(),
    )

    db_session.commit()

    saved = get_summary_by_article_id(
        db_session,
        article.id,
    )

    assert saved is not None
    assert saved.headline == "Test Headline"
    assert saved.summary_text == "Test Summary"
    assert saved.key_points == ["Point 1", "Point 2"]


def test_save_summary_updates_existing_summary(db_session):
    article = upsert_article(
        db_session,
        url="https://example.com/article",
        source_type="rss",
        source="RSS",
        title="Test Article",
    )

    db_session.commit()

    save_summary(
        db_session,
        article_id=article.id,
        headline="Old Headline",
        summary_text="Old Summary",
        generated_at=utcnow(),
    )

    db_session.commit()

    save_summary(
        db_session,
        article_id=article.id,
        headline="New Headline",
        summary_text="New Summary",
        generated_at=utcnow(),
    )

    db_session.commit()

    summaries = list_summaries(db_session)

    assert len(summaries) == 1
    assert summaries[0].headline == "New Headline"


def test_entity_functions(db_session):
    upsert_article(
        db_session,
        url="https://example.com/article",
        source_type="rss",
        source="RSS",
        title="AI Article",
        entities={
            "company": ["OpenAI"],
        },
    )

    db_session.commit()

    entity = get_entity(
        db_session,
        "OpenAI",
        "company",
    )

    assert entity is not None

    entities = list_entities(
        db_session,
        entity_type="company",
    )

    assert len(entities) == 1
    assert entities[0].name == "OpenAI"

    articles = articles_for_entity(
        db_session,
        "OpenAI",
        "company",
    )

    assert len(articles) == 1
    assert articles[0].title == "AI Article"


def test_topic_functions(db_session):
    topic = get_or_create_topic(
        db_session,
        "Generative AI",
        "Generative AI topic",
    )

    # Current Topic model requires created_at.
    # The repository currently does not provide it.
    # This test intentionally checks the repository behavior.
    db_session.commit()

    assert topic.id is not None
    assert topic.name == "Generative AI"

    found = get_topic(
        db_session,
        "Generative AI",
    )

    assert found is not None

    topics = list_topics(db_session)

    assert len(topics) == 1