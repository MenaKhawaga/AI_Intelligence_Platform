"""Phase 5 — Database: repositories"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional, Sequence
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Article, Category, Entity, Summary, Source, Topic



# Articles


def get_article_by_url(session: Session, url: str) -> Optional[Article]:
    """Look up an article by its canonical URL -- the dedup key."""

    return session.execute(select(Article).where(Article.url == url)).scalar_one_or_none()


def get_article_by_id(session: Session, article_id: int) -> Optional[Article]:
    return session.get(Article, article_id)


def _get_or_create_category(session: Session, name: str) -> Category:
    category = session.execute(select(Category).where(Category.name == name)).scalar_one_or_none()
    if category is None:
        category = Category(name=name)
        session.add(category)
        session.flush()  # assigns category.id without ending the caller's transaction
    return category


def _get_or_create_entity(session: Session, name: str, entity_type: str) -> Entity:
    entity = session.execute(
        select(Entity).where(Entity.name == name, Entity.entity_type == entity_type)
    ).scalar_one_or_none()
    if entity is None:
        entity = Entity(name=name, entity_type=entity_type)
        session.add(entity)
        session.flush()
    return entity


def upsert_article(
    session: Session,
    *,
    url: str,
    source_type: str,
    source: str,
    title: str,
    snippet: str = "",
    raw_text: str = "",
    native_score: float = 0.0,
    relevance_score: float = 0.0,
    primary_category: Optional[str] = None,
    categories: Optional[Iterable[str]] = None,
    entities: Optional[Dict[str, Iterable[str]]] = None,
    published_at: Optional[datetime] = None,
    collected_at: Optional[datetime] = None,
    metadata: Optional[dict] = None,
) -> Article:
    """Insert a new article, or update it if ``url`` already exists."""

    article = get_article_by_url(session, url)
    if article is None:
        article = Article(url=url, source_type=source_type, source=source, title=title)
        session.add(article)

    article.source_type = source_type
    article.source = source
    article.title = title
    article.snippet = snippet
    article.raw_text = raw_text
    article.native_score = native_score
    article.relevance_score = relevance_score
    article.primary_category = primary_category
    if published_at is not None:
        article.published_at = published_at
    if collected_at is not None:
        article.collected_at = collected_at
    if metadata is not None:
        article.extra_metadata = metadata

    if categories:
        existing_names = {c.name for c in article.categories}
        for name in categories:
            if name in existing_names:
                continue
            article.categories.append(_get_or_create_category(session, name))
            existing_names.add(name)

    if entities:
        existing_pairs = {(e.name, e.entity_type) for e in article.entities}
        for entity_type, names in entities.items():
            for name in names:
                if (name, entity_type) in existing_pairs:
                    continue
                article.entities.append(_get_or_create_entity(session, name, entity_type))
                existing_pairs.add((name, entity_type))

    session.flush()
    return article


def list_articles(
    session: Session,
    *,
    source_type: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    order_by_relevance: bool = True,
) -> List[Article]:
    """Fetch articles, optionally filtered, ranked by relevance by default."""

    stmt = select(Article)
    if source_type is not None:
        stmt = stmt.where(Article.source_type == source_type)
    if category is not None:
        stmt = stmt.join(Article.categories).where(Category.name == category)
    if order_by_relevance:
        stmt = stmt.order_by(Article.relevance_score.desc())
    stmt = stmt.offset(offset).limit(limit)
    return list(session.execute(stmt).scalars().unique())


# Summaries


def save_summary(
    session: Session,
    *,
    article_id: int,
    headline: str,
    summary_text: str,
    why_it_matters: str = "",
    key_points: Optional[Sequence[str]] = None,
    generated_at: Optional[datetime] = None,
) -> Summary:
    """Create or update the (one-to-one) summary for an article."""

    summary = session.execute(
        select(Summary).where(Summary.article_id == article_id)
    ).scalar_one_or_none()

    if summary is None:
        summary = Summary(article_id=article_id, headline=headline, summary_text=summary_text)
        session.add(summary)

    summary.headline = headline
    summary.summary_text = summary_text
    summary.why_it_matters = why_it_matters
    summary.key_points = list(key_points) if key_points is not None else []
    if generated_at is not None:
        summary.generated_at = generated_at

    session.flush()
    return summary


def get_summary_by_article_id(session: Session, article_id: int) -> Optional[Summary]:
    return session.execute(select(Summary).where(Summary.article_id == article_id)).scalar_one_or_none()


def list_summaries(session: Session, *, limit: int = 50, offset: int = 0) -> List[Summary]:
    """Most-recently-generated summaries first."""

    stmt = select(Summary).order_by(Summary.generated_at.desc()).offset(offset).limit(limit)
    return list(session.execute(stmt).scalars().all())


# Entities


def get_entity(session: Session, name: str, entity_type: str) -> Optional[Entity]:
    return session.execute(
        select(Entity).where(Entity.name == name, Entity.entity_type == entity_type)
    ).scalar_one_or_none()


def list_entities(session: Session, *, entity_type: Optional[str] = None) -> List[Entity]:
    stmt = select(Entity)
    if entity_type is not None:
        stmt = stmt.where(Entity.entity_type == entity_type)
    stmt = stmt.order_by(Entity.name)
    return list(session.execute(stmt).scalars().all())


def articles_for_entity(session: Session, name: str, entity_type: str) -> List[Article]:
    entity = get_entity(session, name, entity_type)
    return list(entity.articles) if entity else []


# Topics


def get_or_create_topic(session: Session, name: str, description: Optional[str] = None) -> Topic:
    topic = session.execute(select(Topic).where(Topic.name == name)).scalar_one_or_none()
    if topic is None:
        topic = Topic(name=name, description=description, created_at=datetime.now(timezone.utc))
        session.add(topic)
        session.flush()
    elif description is not None:
        topic.description = description
    return topic


def get_topic(session: Session, name: str) -> Optional[Topic]:
    return session.execute(select(Topic).where(Topic.name == name)).scalar_one_or_none()


def list_topics(session: Session) -> List[Topic]:
    return list(session.execute(select(Topic).order_by(Topic.name)).scalars().all())


def link_article_to_topic(session: Session, article: Article, topic: Topic) -> None:
    """Associate article with topic (a no-op if already linked)."""

    if topic not in article.topics:
        article.topics.append(topic)
        session.flush()


def articles_for_topic(session: Session, name: str) -> List[Article]:
    topic = get_topic(session, name)
    return list(topic.articles) if topic else []


# Sources


def get_source(session: Session, name: str) -> Optional[Source]:
    return session.execute(
        select(Source).where(Source.name == name)
    ).scalar_one_or_none()


def list_sources(session: Session, *, active_only: bool = False) -> List[Source]:
    stmt = select(Source).order_by(Source.name)

    if active_only:
        stmt = stmt.where(Source.is_active.is_(True))

    return list(session.execute(stmt).scalars().all())


def create_source(
    session: Session,
    *,
    name: str,
    source_type: str,
    url: str,
    is_active: bool = True,
) -> Source:
    source = get_source(session, name)

    if source is None:
        source = Source(
            name=name,
            source_type=source_type,
            url=url,
            is_active=is_active,
        )
        session.add(source)
    else:
        source.source_type = source_type
        source.url = url
        source.is_active = is_active

    session.flush()
    return source