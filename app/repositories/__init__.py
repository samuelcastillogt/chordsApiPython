"""Storage: the repository the API uses, built once from the settings.

`get_repository` is a FastAPI dependency, so tests swap in `InMemoryRepository` with
`app.dependency_overrides[get_repository]`.
"""

import base64
import binascii
import json
import logging
from functools import lru_cache

from fastapi import HTTPException, status

from app.core.config import settings
from app.repositories.base import ProgressionRecord, Repository, RepositoryUnavailableError, UserRecord

__all__ = [
    "ProgressionRecord",
    "Repository",
    "RepositoryUnavailableError",
    "UserRecord",
    "get_repository",
    "optional_repository",
    "repository_available",
]

logger = logging.getLogger(__name__)


def service_account_info(raw: str) -> dict:
    """Service account key from FIREBASE_SERVICE_ACCOUNT: the JSON itself or base64 of it."""
    text = raw.strip()
    if not text.startswith("{"):
        try:
            text = base64.b64decode(text, validate=True).decode()
        except (binascii.Error, UnicodeDecodeError) as error:
            raise RepositoryUnavailableError("FIREBASE_SERVICE_ACCOUNT no es JSON ni base64 de un JSON") from error
    try:
        info = json.loads(text)
    except json.JSONDecodeError as error:
        raise RepositoryUnavailableError("FIREBASE_SERVICE_ACCOUNT no es un JSON válido") from error
    if info.get("type") != "service_account":
        raise RepositoryUnavailableError("FIREBASE_SERVICE_ACCOUNT no es la llave de una cuenta de servicio")
    return info


@lru_cache(maxsize=1)
def _build_repository() -> Repository:
    """Firestore client from the settings. Without FIREBASE_SERVICE_ACCOUNT it falls back to
    Application Default Credentials (GOOGLE_APPLICATION_CREDENTIALS, Google Cloud) or to the
    emulator when FIRESTORE_EMULATOR_HOST is set."""
    if not settings.firebase_project_id:
        raise RepositoryUnavailableError("FIREBASE_PROJECT_ID no está configurado")

    from google.auth.exceptions import GoogleAuthError
    from google.cloud.firestore import AsyncClient
    from google.oauth2 import service_account

    from app.repositories.firestore import FirestoreRepository

    credentials = None
    if settings.firebase_service_account:
        credentials = service_account.Credentials.from_service_account_info(service_account_info(settings.firebase_service_account))
    try:
        client = AsyncClient(project=settings.firebase_project_id, credentials=credentials, database=settings.firestore_database)
    except GoogleAuthError as error:
        raise RepositoryUnavailableError("No hay credenciales para Firestore: define FIREBASE_SERVICE_ACCOUNT") from error
    return FirestoreRepository(client, prefix=settings.firestore_collection_prefix)


def repository_available(log: bool = False) -> bool:
    try:
        _build_repository()
    except RepositoryUnavailableError as error:
        if log:
            logger.warning("Firestore is unavailable, accounts are disabled: %s", error)
        return False
    return True


def get_repository() -> Repository:
    try:
        return _build_repository()
    except RepositoryUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"La base de datos no está disponible: {error}"
        ) from error


def optional_repository() -> Repository | None:
    """Like `get_repository`, but None instead of 503 (for /health)."""
    try:
        return _build_repository()
    except RepositoryUnavailableError:
        return None
