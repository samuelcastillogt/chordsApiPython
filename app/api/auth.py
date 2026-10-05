from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AuthRequest, TokenResponse, UserResponse
from app.core.security import (
    EMAIL_RE,
    create_access_token,
    get_current_user,
    hash_password,
    require_auth_enabled,
    verify_password,
)
from app.db import get_session
from app.models import User

router = APIRouter()


def serialize_user(user: User) -> dict:
    return {"id": user.id, "email": user.email, "displayName": user.display_name}


def token_response(user: User) -> dict:
    return {"accessToken": create_access_token(user.id), "user": serialize_user(user)}


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: AuthRequest, session: AsyncSession = Depends(get_session)):
    require_auth_enabled()
    email = request.email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Email inválido")
    existing = await session.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    user = User(email=email, display_name=(request.displayName or "").strip() or None, password_hash=hash_password(request.password))
    session.add(user)
    await session.commit()
    return token_response(user)


@router.post("/auth/login", response_model=TokenResponse)
async def login(request: AuthRequest, session: AsyncSession = Depends(get_session)):
    require_auth_enabled()
    user = await session.scalar(select(User).where(User.email == request.email.strip().lower()))
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return token_response(user)


@router.get("/auth/me", response_model=UserResponse)
async def me(user: User = Depends(get_current_user)):
    return serialize_user(user)
