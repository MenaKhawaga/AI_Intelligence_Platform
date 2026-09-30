from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, Integer, String, Table, Column, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base_class import Base

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


article_categories = Table(
    "article_categories",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("articles.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True)
)

article_entities = Table(
    "article_entities",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("articles.id"), primary_key=True),
    Column("entity_id", Integer, ForeignKey("entities.id"), primary_key=True)
)

article_topics = Table(
    "article_topics",
    Base.metadata,
    Column("article_id", Integer, ForeignKey("articles.id"), primary_key=True),
    Column("topic_id", Integer, ForeignKey("topics.id"), primary_key=True)
)


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    url: Mapped[str] = mapped_column(String(1000), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    native_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    relevance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    primary_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extra_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    summary = relationship("Summary", back_populates="article", uselist=False)
    categories = relationship("Category", secondary="article_categories", back_populates="articles")
    entities = relationship("Entity", secondary="article_entities", back_populates="articles")
    topics = relationship("Topic", secondary="article_topics", back_populates="articles")