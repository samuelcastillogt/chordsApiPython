"""Verification of Firebase Authentication ID tokens.

Follows Firebase's "verify ID tokens using a third-party JWT library" procedure, so the API
needs neither a service account nor the firebase-admin SDK: tokens are RS256 JWTs signed by
Google, checked against its public keys (cached for as long as Google's Cache-Control allows)
and against the project id (audience and issuer).
"""

import json
import re
import threading
import time
import urllib.request
from dataclasses import dataclass

from jose import jwt
from jose.exceptions import JOSEError

JWKS_URL = "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com"
DEFAULT_KEYS_TTL = 3600
CLOCK_SKEW_SECONDS = 60
MAX_AGE_RE = re.compile(r"max-age=(\d+)")


class InvalidTokenError(Exception):
    """The token is missing, malformed, expired or not issued for this project."""


@dataclass(frozen=True)
class FirebaseIdentity:
    uid: str
    email: str | None
    email_verified: bool
    name: str | None
    picture: str | None
    provider: str | None


class _KeyCache:
    def __init__(self) -> None:
        self._keys: dict[str, dict] = {}
        self._expires_at = 0.0
        self._lock = threading.Lock()

    def get(self, kid: str) -> dict | None:
        with self._lock:
            if kid not in self._keys or time.time() >= self._expires_at:
                self._keys, ttl = fetch_keys()
                self._expires_at = time.time() + ttl
            return self._keys.get(kid)

    def clear(self) -> None:
        with self._lock:
            self._keys, self._expires_at = {}, 0.0


def fetch_keys() -> tuple[dict[str, dict], int]:
    """Google's current signing keys by key id, and how long they may be cached."""
    try:
        with urllib.request.urlopen(JWKS_URL, timeout=5) as response:
            body = json.load(response)
            match = MAX_AGE_RE.search(response.headers.get("Cache-Control", ""))
    except (OSError, ValueError) as error:
        raise InvalidTokenError("No se pudieron obtener las llaves públicas de Firebase") from error
    keys = {key["kid"]: key for key in body.get("keys", []) if "kid" in key}
    return keys, int(match.group(1)) if match else DEFAULT_KEYS_TTL


key_cache = _KeyCache()


def _verified_claims(token: str, project_id: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except JOSEError as error:
        raise InvalidTokenError("Token mal formado") from error
    if header.get("alg") != "RS256" or not header.get("kid"):
        raise InvalidTokenError("Algoritmo o llave del token no válidos")
    key = key_cache.get(header["kid"])
    if key is None:
        raise InvalidTokenError("El token está firmado con una llave desconocida")
    try:
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience=project_id,
            issuer=f"https://securetoken.google.com/{project_id}",
            options={"leeway": CLOCK_SKEW_SECONDS},
        )
    except JOSEError as error:
        raise InvalidTokenError("Token expirado o emitido para otro proyecto") from error


def _emulator_claims(token: str, project_id: str) -> dict:
    """The Auth emulator issues unsigned tokens: same checks, minus the signature."""
    try:
        claims = jwt.get_unverified_claims(token)
    except JOSEError as error:
        raise InvalidTokenError("Token mal formado") from error
    if claims.get("aud") != project_id or claims.get("iss") != f"https://securetoken.google.com/{project_id}":
        raise InvalidTokenError("Token emitido para otro proyecto")
    if claims.get("exp", 0) < time.time() - CLOCK_SKEW_SECONDS:
        raise InvalidTokenError("Token expirado")
    return claims


def verify_id_token(token: str, project_id: str, emulator: bool = False) -> FirebaseIdentity:
    """Identity in a Firebase ID token. ``emulator`` skips the signature: never use it in production."""
    if not token or not project_id:
        raise InvalidTokenError("Token vacío o proyecto de Firebase sin configurar")
    claims = _emulator_claims(token, project_id) if emulator else _verified_claims(token, project_id)

    uid = claims.get("sub")
    if not isinstance(uid, str) or not uid or len(uid) > 128:
        raise InvalidTokenError("El token no identifica a un usuario")
    if claims.get("auth_time", 0) > time.time() + CLOCK_SKEW_SECONDS:
        raise InvalidTokenError("La fecha de autenticación del token está en el futuro")

    return FirebaseIdentity(
        uid=uid,
        email=(claims.get("email") or "").lower() or None,
        email_verified=bool(claims.get("email_verified")),
        name=claims.get("name"),
        picture=claims.get("picture"),
        provider=(claims.get("firebase") or {}).get("sign_in_provider"),
    )
