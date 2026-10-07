import pytest

from app.core.firebase import InvalidTokenError, verify_id_token
from tests.firebase_fakes import PROJECT_ID, id_token


def test_valid_token_returns_the_identity():
    identity = verify_id_token(id_token(uid="abc", email="Ana@Example.com", name="Ana"), PROJECT_ID)

    assert identity.uid == "abc"
    assert identity.email == "ana@example.com"
    assert identity.email_verified is True
    assert identity.name == "Ana"
    assert identity.provider == "password"


@pytest.mark.parametrize(
    "token",
    [
        "",
        "not-a-jwt",
        id_token(project="another-project"),
        id_token(expires_in=-3600),
        id_token(kid="unknown-key"),
    ],
    ids=["empty", "malformed", "other-project", "expired", "unknown-key"],
)
def test_invalid_tokens_are_rejected(token):
    with pytest.raises(InvalidTokenError):
        verify_id_token(token, PROJECT_ID)


def test_project_id_is_required():
    with pytest.raises(InvalidTokenError):
        verify_id_token(id_token(), "")


def unsigned_token(project: str = PROJECT_ID, expires_in: int = 3600) -> str:
    import base64
    import json
    import time

    def part(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    now = int(time.time())
    claims = {
        "iss": f"https://securetoken.google.com/{project}",
        "aud": project,
        "sub": "emulated-user",
        "auth_time": now,
        "exp": now + expires_in,
        "email": "emu@example.com",
    }
    return f"{part({'alg': 'none', 'typ': 'JWT'})}.{part(claims)}."


def test_emulator_tokens_are_only_accepted_in_emulator_mode():
    token = unsigned_token()

    assert verify_id_token(token, PROJECT_ID, emulator=True).uid == "emulated-user"
    with pytest.raises(InvalidTokenError):
        verify_id_token(token, PROJECT_ID)
    with pytest.raises(InvalidTokenError):
        verify_id_token(unsigned_token(project="other"), PROJECT_ID, emulator=True)
    with pytest.raises(InvalidTokenError):
        verify_id_token(unsigned_token(expires_in=-3600), PROJECT_ID, emulator=True)
