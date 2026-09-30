from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.api.dependencies import current_user, db_session
from app.services.auth_service import authenticate, create_access_token, create_user

router = APIRouter(prefix="/auth", tags=["authentication"])


class Credentials(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", status_code=201)
def register(payload: Credentials, session=Depends(db_session)):
    try:
        user = create_user(session, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"id": user.id, "email": user.email}


@router.post("/login", response_model=TokenResponse)
def login(payload: Credentials, session=Depends(db_session)):
    user = authenticate(session, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(access_token=create_access_token(user))


@router.get("/me")
def me(user=Depends(current_user)):
    return {
            "id": user.id,
            "email": user.email,
            "active": user.is_active,
            "is_admin": user.is_admin,
               }
