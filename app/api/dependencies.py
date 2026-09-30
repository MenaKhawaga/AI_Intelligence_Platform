"""Shared FastAPI dependencies for sessions and authenticated requests."""
from __future__ import annotations

from typing import Generator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.config import settings
from app.database.session import get_session
from app.models.user import User

bearer = HTTPBearer(auto_error=False)


def db_session() -> Generator:
    with get_session() as session:
        yield session


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session=Depends(db_session),
) -> User:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    try:
        payload = jwt.decode(credentials.credentials, settings.JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")
    user = session.execute(select(User).where(User.id == user_id, User.is_active.is_(True))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


# def admin_user(user: User = Depends(current_user)) -> User:
#     if not user.is_admin:

#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Admin access required",
#         )
    
#     return user

def admin_user(user: User = Depends(current_user)) -> User:
    print("ADMIN CHECK:", user.id, user.email, user.is_admin)

    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return user