import base64
import json

import pytest

from app.core.config import Settings
from app.repositories import RepositoryUnavailableError
from app.repositories import service_account_info as parse_service_account

KEY = {"type": "service_account", "project_id": "chordweaver", "client_email": "api@chordweaver.iam.gserviceaccount.com"}


def test_accounts_need_a_firebase_project(monkeypatch):
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "  ")
    assert Settings().auth_enabled is False

    monkeypatch.setenv("FIREBASE_PROJECT_ID", "chordweaver-prod")
    assert Settings().auth_enabled is True


def test_cors_origins_are_split_and_trimmed(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example.com, http://localhost:3000 ,")

    assert Settings().cors_origin_list == ["https://a.example.com", "http://localhost:3000"]


def test_auth_emulator_is_never_used_in_production(monkeypatch):
    monkeypatch.setenv("FIREBASE_AUTH_EMULATOR_HOST", "127.0.0.1:9099")
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert Settings().uses_auth_emulator is True

    monkeypatch.setenv("ENVIRONMENT", "production")
    assert Settings().uses_auth_emulator is False

    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("VERCEL", "1")
    assert Settings().uses_auth_emulator is False


def test_service_account_accepts_json_or_base64():
    raw = json.dumps(KEY)

    assert parse_service_account(raw) == KEY
    assert parse_service_account(f"  {raw}\n") == KEY
    assert parse_service_account(base64.b64encode(raw.encode()).decode()) == KEY


@pytest.mark.parametrize("raw", ["not json", "{broken", base64.b64encode(b'{"type": "authorized_user"}').decode()])
def test_service_account_rejects_anything_else(raw):
    with pytest.raises(RepositoryUnavailableError):
        parse_service_account(raw)
