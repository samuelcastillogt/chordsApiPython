import os
import sys
from pathlib import Path

import pytest

# Settings for the whole test session (set before app import).
os.environ["FIREBASE_PROJECT_ID"] = "test-project"
os.environ["FIREBASE_SERVICE_ACCOUNT"] = ""
os.environ["ENVIRONMENT"] = "test"
os.environ.pop("VERCEL", None)

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core import firebase
from app.main import app
from app.repositories import get_repository, optional_repository
from app.repositories.memory import InMemoryRepository
from tests.firebase_fakes import fake_fetch_keys


@pytest.fixture(autouse=True)
def firebase_test_keys(monkeypatch):
    """Tokens are verified for real, against a local key instead of Google's."""
    monkeypatch.setattr(firebase, "fetch_keys", fake_fetch_keys)
    firebase.key_cache.clear()
    yield
    firebase.key_cache.clear()


@pytest.fixture(autouse=True)
def repository():
    """Each test gets an empty in-memory store instead of Firestore."""
    store = InMemoryRepository()
    app.dependency_overrides[get_repository] = lambda: store
    app.dependency_overrides[optional_repository] = lambda: store
    yield store
    app.dependency_overrides.pop(get_repository, None)
    app.dependency_overrides.pop(optional_repository, None)
