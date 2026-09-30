"""Shared fixtures for tests/graph/.

Every test gets its own in-memory SQLite database, exposed the same way
production exposes one: as a ``session_scope`` callable returning a
commit-on-success / rollback-on-error context manager (the shape of
``app.database.session.get_session``).
"""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Callable, Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import Article, Summary
from app.database.session import create_engine_from_url, create_session_factory, init_db


@pytest.fixture()
def session_scope() -> Iterator[Callable]:
    engine = create_engine_from_url("sqlite:///:memory:")
    init_db(engine)
    factory = create_session_factory(engine)

    @contextmanager
    def scope() -> Iterator[Session]:
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    try:
        yield scope
    finally:
        engine.dispose()


@pytest.fixture()
def db_read(session_scope):
    """Read back what was stored: ``db_read()`` -> (articles, summaries)."""

    def read():
        with session_scope() as session:
            articles = list(session.execute(select(Article).order_by(Article.url)).scalars().unique())
            summaries = list(session.execute(select(Summary)).scalars())
            # Touch lazy relationships before the session closes.
            for a in articles:
                _ = [c.name for c in a.categories], [e.name for e in a.entities]
            return SimpleNamespace(articles=articles, summaries=summaries)

    return read


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    """Summarization retries failed LLM calls with a 1s sleep; skip the wait in tests."""

    import app.collectors.base as base

    async def instant_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr(base, "asyncio", SimpleNamespace(sleep=instant_sleep))
