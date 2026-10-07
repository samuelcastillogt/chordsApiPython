import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import repositories
from app.core.config import settings
from app.main import app
from app.repositories import RepositoryUnavailableError, get_repository, optional_repository
from app.repositories.firestore import FirestoreRepository
from tests.firebase_fakes import auth_headers


@pytest.fixture(autouse=True)
def fresh_factory():
    repositories._build_repository.cache_clear()
    yield
    repositories._build_repository.cache_clear()


def test_firestore_needs_a_project(monkeypatch):
    monkeypatch.setattr(settings, "firebase_project_id", "")

    with pytest.raises(RepositoryUnavailableError, match="FIREBASE_PROJECT_ID"):
        repositories._build_repository()
    assert optional_repository() is None
    with pytest.raises(HTTPException) as error:
        get_repository()
    assert error.value.status_code == 503


def test_invalid_service_account_is_reported(monkeypatch):
    monkeypatch.setattr(settings, "firebase_service_account", "not-a-key")

    with pytest.raises(RepositoryUnavailableError, match="FIREBASE_SERVICE_ACCOUNT"):
        repositories._build_repository()


def test_emulator_builds_a_firestore_repository_without_credentials(monkeypatch):
    monkeypatch.setenv("FIRESTORE_EMULATOR_HOST", "127.0.0.1:8080")
    monkeypatch.setattr(settings, "firebase_service_account", "")

    repository = repositories._build_repository()

    assert isinstance(repository, FirestoreRepository)
    assert repository.client.project == "test-project"
    assert (repository.users, repository.progressions) == ("chordweaver_users", "chordweaver_progressions")


def test_api_degrades_to_503_when_firestore_is_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "firebase_project_id", "")
    app.dependency_overrides.pop(get_repository, None)
    app.dependency_overrides.pop(optional_repository, None)
    client = TestClient(app)

    assert client.get("/health").json()["accounts"] is False
    assert client.get("/api/v1/progressions", headers=auth_headers()).status_code == 503
    # Stateless endpoints keep working.
    assert client.post("/api/v1/analyze", json={"chords": ["C", "G"]}).status_code == 200
