from __future__ import annotations

from app.models.article import Article
from app.models.user import User


def test_user_crud(db_session):
    # -----------------
    # INSERT
    # -----------------
    user = User(
        email="test@example.com",
        password_hash="hashed-password",
    )

    db_session.add(user)
    db_session.commit()

    assert user.id is not None

    # -----------------
    # SELECT
    # -----------------
    saved_user = db_session.get(
        User,
        user.id,
    )

    assert saved_user is not None
    assert saved_user.email == "test@example.com"
    assert saved_user.is_active is True
    assert saved_user.is_admin is False

    # -----------------
    # UPDATE
    # -----------------
    saved_user.is_active = False

    db_session.commit()

    updated_user = db_session.get(
        User,
        user.id,
    )

    assert updated_user is not None
    assert updated_user.is_active is False

    # -----------------
    # DELETE
    # -----------------
    db_session.delete(updated_user)
    db_session.commit()

    deleted_user = db_session.get(
        User,
        user.id,
    )

    assert deleted_user is None


def test_article_crud(db_session):
    # -----------------
    # INSERT
    # -----------------
    article = Article(
        url="https://example.com/test",
        source_type="rss",
        source="Test Source",
        title="Original Title",
        snippet="Original snippet",
    )

    db_session.add(article)
    db_session.commit()

    assert article.id is not None

    # -----------------
    # SELECT
    # -----------------
    saved_article = db_session.get(
        Article,
        article.id,
    )

    assert saved_article is not None
    assert saved_article.title == "Original Title"

    # -----------------
    # UPDATE
    # -----------------
    saved_article.title = "Updated Title"
    saved_article.snippet = "Updated snippet"

    db_session.commit()

    updated_article = db_session.get(
        Article,
        article.id,
    )

    assert updated_article is not None
    assert updated_article.title == "Updated Title"
    assert updated_article.snippet == "Updated snippet"

    # -----------------
    # DELETE
    # -----------------
    db_session.delete(updated_article)
    db_session.commit()

    deleted_article = db_session.get(
        Article,
        article.id,
    )

    assert deleted_article is None