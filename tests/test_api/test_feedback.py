from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from tests.firebase_fakes import auth_headers

client = TestClient(app)


def test_anonymous_feedback_is_stored(repository):
    response = client.post("/api/v1/feedback", json={"message": "  Me encanta el explorador  ", "rating": 5, "page": "/explorer/"})

    assert response.status_code == 201 and response.json()["received"] is True
    stored = repository.feedback[0]
    assert stored.message == "Me encanta el explorador" and stored.rating == 5 and stored.user_id is None and stored.source == "web"


def test_signed_in_feedback_is_linked_to_the_user(repository):
    client.post(
        "/api/v1/feedback",
        json={"message": "Falta el modo alabanza", "source": "app"},
        headers=auth_headers(uid="ana", email="ana@example.com"),
    )

    stored = repository.feedback[0]
    assert stored.user_id == "ana" and stored.email == "ana@example.com" and stored.source == "app"


def test_feedback_is_validated_and_bots_are_ignored(repository):
    assert client.post("/api/v1/feedback", json={"message": "x"}).status_code == 422
    assert client.post("/api/v1/feedback", json={"message": "hola mundo", "rating": 9}).status_code == 422
    bot = client.post("/api/v1/feedback", json={"message": "compra ya", "website": "http://spam"})
    assert bot.status_code == 201 and repository.feedback == []


def test_monitoring_test_route_is_hidden_without_the_token(monkeypatch):
    assert client.get("/api/v1/monitoring/test").status_code == 404
    monkeypatch.setattr(settings, "monitoring_test_token", "secreto")
    assert client.get("/api/v1/monitoring/test", headers={"X-Test-Token": "otro"}).status_code == 404
    raising = TestClient(app, raise_server_exceptions=False)
    assert raising.get("/api/v1/monitoring/test", headers={"X-Test-Token": "secreto"}).status_code == 500
