from datetime import timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.repositories.base import utcnow
from tests.firebase_fakes import auth_headers

client = TestClient(app)


def test_first_request_creates_the_user_from_the_token(repository):
    headers = auth_headers(uid="ana-uid", email="ana@example.com", name="Ana")

    first = client.get("/api/v1/auth/me", headers=headers)
    second = client.get("/api/v1/auth/me", headers=headers)

    assert first.status_code == 200
    assert first.json() == {"id": "ana-uid", "email": "ana@example.com", "displayName": "Ana", "photoUrl": None}
    assert second.json()["id"] == "ana-uid"
    assert set(repository.users) == {"ana-uid"}


def test_last_login_is_written_at_most_once_per_hour(repository):
    headers = auth_headers(uid="busy-uid")
    client.get("/api/v1/auth/me", headers=headers)
    first_login = repository.users["busy-uid"].last_login_at

    client.get("/api/v1/auth/me", headers=headers)
    assert repository.users["busy-uid"].last_login_at == first_login

    repository.users["busy-uid"].last_login_at = utcnow() - timedelta(hours=2)
    client.get("/api/v1/auth/me", headers=headers)
    assert repository.users["busy-uid"].last_login_at > first_login


def test_display_name_can_be_changed_and_cleared():
    headers = auth_headers(name="Gus")

    renamed = client.patch("/api/v1/auth/me", json={"displayName": "  Gustavo "}, headers=headers)
    assert renamed.json()["displayName"] == "Gustavo"
    cleared = client.patch("/api/v1/auth/me", json={"displayName": ""}, headers=headers)
    assert cleared.json()["displayName"] is None
    # The provider's name does not come back on later requests.
    assert client.get("/api/v1/auth/me", headers=headers).json()["displayName"] is None
    untouched = client.patch("/api/v1/auth/me", json={}, headers=headers)
    assert untouched.json()["displayName"] is None


def test_deleting_the_account_removes_its_progressions(repository):
    headers = auth_headers(uid="leaving-uid")
    progression = client.post(
        "/api/v1/progressions", json={"name": "Adiós", "chords": ["C", "G"], "isPublic": True}, headers=headers
    ).json()

    assert client.delete("/api/v1/auth/me", headers=headers).status_code == 204
    assert repository.users == {} and repository.progressions == {}
    assert client.get(f"/api/v1/progressions/{progression['id']}").status_code == 404


def test_requests_without_a_valid_token_are_rejected():
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"}).status_code == 401
    assert client.get("/api/v1/auth/me", headers=auth_headers(project="someone-else")).status_code == 401
    assert client.get("/api/v1/auth/me", headers=auth_headers(expires_in=-120)).status_code == 401


def test_accounts_are_disabled_without_a_firebase_project(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "firebase_project_id", "")

    response = client.get("/api/v1/auth/me", headers=auth_headers())
    assert response.status_code == 503
    assert "FIREBASE_PROJECT_ID" in response.json()["detail"]
    assert client.get("/health").json()["accounts"] is False
