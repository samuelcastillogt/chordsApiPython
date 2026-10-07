"""Request authentication: Firebase ID tokens in the `Authorization: Bearer` header."""

from datetime import timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.firebase import FirebaseIdentity, InvalidTokenError, verify_id_token
from app.repositories import Repository, UserRecord, get_repository
from app.repositories.base import utcnow

bearer = HTTPBearer(auto_error=False)
# How often the last sign-in time is written, so authenticated reads do not always write.
LOGIN_REFRESH = timedelta(hours=1)


def require_auth_enabled() -> None:
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Las cuentas están deshabilitadas: configura FIREBASE_PROJECT_ID en el servidor",
        )


def _identity(credentials: HTTPAuthorizationCredentials | None) -> FirebaseIdentity | None:
    if credentials is None:
        return None
    try:
        return verify_id_token(credentials.credentials, settings.firebase_project_id, emulator=settings.uses_auth_emulator)
    except InvalidTokenError:
        return None


async def sync_user(identity: FirebaseIdentity, repository: Repository) -> UserRecord:
    """The stored user for a Firebase identity (keyed by its uid), created on first sign-in.

    The provider's name only seeds the profile: users can change or clear it afterwards.
    Writes happen on creation, when email or photo change, or once per LOGIN_REFRESH.
    """
    user = await repository.get_user(identity.uid)
    if user is None:
        user = UserRecord(id=identity.uid, email=identity.email, display_name=(identity.name or "").strip()[:80] or None)
        stale = True
    else:
        stale = user.last_login_at is None or utcnow() - user.last_login_at > LOGIN_REFRESH
    photo_url = identity.picture or user.photo_url
    if stale or user.email != identity.email or user.photo_url != photo_url:
        user.email = identity.email
        user.photo_url = photo_url
        user.last_login_at = utcnow()
        await repository.save_user(user)
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    repository: Repository = Depends(get_repository),
) -> UserRecord:
    require_auth_enabled()
    identity = _identity(credentials)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inicia sesión para continuar",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await sync_user(identity, repository)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    repository: Repository = Depends(get_repository),
) -> UserRecord | None:
    if not settings.auth_enabled:
        return None
    identity = _identity(credentials)
    return await sync_user(identity, repository) if identity else None
