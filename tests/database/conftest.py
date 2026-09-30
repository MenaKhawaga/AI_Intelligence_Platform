from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.base_class import Base

from app.models.agent_activity import AgentActivity
from app.models.article import Article
from app.models.category import Category
from app.models.entity import Entity
from app.models.source import Source
from app.models.summary import Summary
from app.models.topic import Topic
from app.models.user import User


load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")


@pytest.fixture()
def db_session():
    if not TEST_DATABASE_URL:
        raise RuntimeError(
            "TEST_DATABASE_URL is not set in the environment."
        )

    engine = create_engine(TEST_DATABASE_URL)

    # Start every test with a clean database.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()

        # Remove test tables after the test.
        Base.metadata.drop_all(bind=engine)

        engine.dispose()