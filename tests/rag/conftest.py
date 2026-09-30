"""Shared fixtures for RAG tests."""

from __future__ import annotations

from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import session as session_module
from app.database.base_class import Base

# Import all models so they are registered in Base.metadata.
from app.models.agent_activity import AgentActivity  # noqa: F401
from app.models.article import Article  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.entity import Entity  # noqa: F401
from app.models.source import Source  # noqa: F401
from app.models.summary import Summary  # noqa: F401
from app.models.topic import Topic  # noqa: F401
from app.models.user import User  # noqa: F401


@pytest.fixture()
def rag_env(tmp_path, monkeypatch) -> Iterator[None]:

    db_url = f"sqlite:///{tmp_path / 'rag-test.db'}"
    engine = create_engine(db_url)
    test_session_local = sessionmaker(autocommit=False,autoflush=False,bind=engine,)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(session_module,"SessionLocal",test_session_local,)
    monkeypatch.setattr("app.core.config.settings.CHROMA_PATH",str(tmp_path / "chroma"),)

    try:
        yield

    finally:
        engine.dispose()