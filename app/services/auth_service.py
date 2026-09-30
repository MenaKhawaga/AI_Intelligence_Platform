"""Authentication and signed access-token helpers."""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import User


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_user(session: Session, email: str, password: str) -> User:
    email = email.strip().lower()
    if not email or "@" not in email:
        raise ValueError("A valid email is required")
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    if session.execute(select(User).where(User.email == email)).scalar_one_or_none():
        raise ValueError("Email is already registered")
    user = User(email=email, password_hash=hash_password(password))
    session.add(user)
    session.flush()
    return user


def authenticate(session: Session, email: str, password: str) -> User | None:
    user = session.execute(select(User).where(User.email == email.strip().lower())).scalar_one_or_none()
    if user and user.is_active and verify_password(password, user.password_hash):
        return user
    return None


def create_access_token(user: User) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user.id), "email": user.email, "exp": expires}, settings.JWT_SECRET_KEY, algorithm="HS256")
