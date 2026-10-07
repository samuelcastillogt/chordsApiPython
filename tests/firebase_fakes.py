"""Signs Firebase-like ID tokens with a test RSA key that replaces Google's public keys."""

import time
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwk, jwt

PROJECT_ID = "test-project"
KEY_ID = "test-key"

_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_PEM = _private_key.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
).decode()
PUBLIC_JWK = {
    **jwk.construct(
        _private_key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode(),
        "RS256",
    ).to_dict(),
    "kid": KEY_ID,
    "use": "sig",
}


def fake_fetch_keys() -> tuple[dict[str, dict], int]:
    return {KEY_ID: PUBLIC_JWK}, 3600


def id_token(
    uid: str | None = None,
    email: str | None = None,
    verified: bool = True,
    name: str | None = None,
    project: str = PROJECT_ID,
    expires_in: int = 3600,
    kid: str = KEY_ID,
) -> str:
    now = int(time.time())
    uid = uid or f"uid-{uuid4().hex[:12]}"
    claims = {
        "iss": f"https://securetoken.google.com/{project}",
        "aud": project,
        "sub": uid,
        "user_id": uid,
        "iat": now,
        "auth_time": now,
        "exp": now + expires_in,
        "email": email if email is not None else f"{uid}@example.com",
        "email_verified": verified,
        "firebase": {"sign_in_provider": "password"},
    }
    if name:
        claims["name"] = name
    return jwt.encode(claims, PRIVATE_PEM, algorithm="RS256", headers={"kid": kid})


def auth_headers(**kwargs) -> dict[str, str]:
    return {"Authorization": f"Bearer {id_token(**kwargs)}"}
