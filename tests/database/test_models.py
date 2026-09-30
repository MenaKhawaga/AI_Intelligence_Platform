from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.article import Article
from app.models.category import Category
from app.models.entity import Entity
from app.models.summary import Summary
from app.models.topic import Topic


def utcnow():
    return datetime.now(timezone.utc)


def test_article_url_is_unique(db_session):
    article1 = Article(
        url="https://example.com/article",
        source_type="rss",
        source="Test Source",
        title="Article 1",
    )

    db_session.add(article1)
    db_session.commit()

    article2 = Article(
        url="https://example.com/article",
        source_type="rss",
        source="Test Source",
        title="Article 2",
    )

    db_session.add(article2)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_article_defaults(db_session):
    article = Article(
        url="https://example.com/article",
        source_type="rss",
        source="Test Source",
        title="Test Article",
    )

    db_session.add(article)
    db_session.commit()

    assert article.snippet == ""
    assert article.raw_text == ""
    assert article.native_score == 0.0
    assert article.relevance_score == 0.0
    assert article.extra_metadata == {}
    assert article.created_at is not None
    assert article.collected_at is not None


def test_article_summary_relationship(db_session):
    article = Article(
        url="https://example.com/article",
        source_type="rss",
        source="Test Source",
        title="Test Article",
    )

    db_session.add(article)
    db_session.commit()

    summary = Summary(
        article_id=article.id,
        headline="Test Headline",
        summary_text="Test Summary",
        why_it_matters="Test reason",
        key_points=["Point 1", "Point 2"],
        generated_at=utcnow(),
    )

    db_session.add(summary)
    db_session.commit()

    db_session.refresh(article)

    assert article.summary is not None
    assert article.summary.headline == "Test Headline"
    assert summary.article.id == article.id


def test_summary_article_id_is_unique(db_session):
    article = Article(
        url="https://example.com/article",
        source_type="rss",
        source="Test Source",
        title="Test Article",
    )

    db_session.add(article)
    db_session.commit()

    summary1 = Summary(
        article_id=article.id,
        headline="Headline 1",
        summary_text="Summary 1",
        why_it_matters="Reason 1",
        key_points=[],
        generated_at=utcnow(),
    )

    db_session.add(summary1)
    db_session.commit()

    summary2 = Summary(
        article_id=article.id,
        headline="Headline 2",
        summary_text="Summary 2",
        why_it_matters="Reason 2",
        key_points=[],
        generated_at=utcnow(),
    )

    db_session.add(summary2)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_article_category_many_to_many(db_session):
    article = Article(
        url="https://example.com/article",
        source_type="rss",
        source="Test Source",
        title="Test Article",
    )

    category = Category(name="LLMs")

    article.categories.append(category)

    db_session.add(article)
    db_session.commit()

    db_session.refresh(article)

    assert len(article.categories) == 1
    assert article.categories[0].name == "LLMs"

    assert len(category.articles) == 1
    assert category.articles[0].url == "https://example.com/article"


def test_category_name_is_unique(db_session):
    category1 = Category(name="LLMs")

    db_session.add(category1)
    db_session.commit()

    category2 = Category(name="LLMs")

    db_session.add(category2)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_entity_unique_on_name_and_type(db_session):
    entity1 = Entity(
        name="Claude",
        entity_type="model",
    )

    db_session.add(entity1)
    db_session.commit()

    # Same name but different type is allowed.
    entity2 = Entity(
        name="Claude",
        entity_type="person",
    )

    db_session.add(entity2)
    db_session.commit()

    assert db_session.query(Entity).count() == 2

    # Same name AND same type is not allowed.
    entity3 = Entity(
        name="Claude",
        entity_type="model",
    )

    db_session.add(entity3)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_article_entity_many_to_many(db_session):
    article = Article(
        url="https://example.com/article",
        source_type="rss",
        source="Test Source",
        title="Test Article",
    )

    entity = Entity(
        name="OpenAI",
        entity_type="company",
    )

    article.entities.append(entity)

    db_session.add(article)
    db_session.commit()

    db_session.refresh(article)

    assert len(article.entities) == 1
    assert article.entities[0].name == "OpenAI"
    assert article.entities[0].entity_type == "company"


def test_article_topic_many_to_many(db_session):
    article = Article(
        url="https://example.com/article",
        source_type="rss",
        source="Test Source",
        title="Test Article",
    )

    topic = Topic(
        name="GPT-5",
        created_at=utcnow(),
    )

    article.topics.append(topic)

    db_session.add(article)
    db_session.commit()

    db_session.refresh(article)

    assert len(article.topics) == 1
    assert article.topics[0].name == "GPT-5"

    assert len(topic.articles) == 1
    assert topic.articles[0].url == "https://example.com/article"


def test_topic_name_is_unique(db_session):
    topic1 = Topic(
        name="GPT-5",
        created_at=utcnow(),
    )

    db_session.add(topic1)
    db_session.commit()

    topic2 = Topic(
        name="GPT-5",
        created_at=utcnow(),
    )

    db_session.add(topic2)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()