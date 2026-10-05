import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from jose import jwt

from app.api.schemas import AuthRequest, TokenResponse
from app.core.config import settings

router = APIRouter()
_users: dict[str, dict[str, str]] = {}


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    password_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        password_salt.encode("utf-8"),
        120_000,
    ).hex()
    return password_salt, digest


def create_access_token(email: str) -> str:
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": email, "exp": expires_at}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(request: AuthRequest):
    email = request.email.lower()
    if email in _users:
        raise HTTPException(status_code=409, detail="User already exists")
    salt, password_hash = hash_password(request.password)
    _users[email] = {"salt": salt, "password_hash": password_hash}
    return {"accessToken": create_access_token(email)}


@router.post("/auth/login", response_model=TokenResponse)
async def login(request: AuthRequest):
    email = request.email.lower()
    user = _users.get(email)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    _, password_hash = hash_password(request.password, user["salt"])
    if not secrets.compare_digest(password_hash, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"accessToken": create_access_token(email)}
