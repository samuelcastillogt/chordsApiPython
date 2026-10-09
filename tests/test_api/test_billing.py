from fastapi.testclient import TestClient

from app.domain.plans import FREE_SAVE_LIMIT
from app.main import app
from tests.firebase_fakes import auth_headers

client = TestClient(app)


def save(headers: dict[str, str], name: str = "Prog"):
    return client.post("/api/v1/progressions", json={"name": name, "chords": ["C", "G"]}, headers=headers)


def test_plans_are_public_with_regional_prices():
    body = client.get("/api/v1/plans").json()

    assert body["provider"] == "mock"
    plans = {plan["id"]: plan for plan in body["plans"]}
    assert list(plans) == ["free", "pro", "lifetime"]
    assert plans["free"]["saveLimit"] == FREE_SAVE_LIMIT and plans["free"]["prices"] == []
    pro_prices = {(price["period"], price["region"]): price["amount"] for price in plans["pro"]["prices"]}
    assert pro_prices == {("monthly", "global"): 4.99, ("yearly", "global"): 29.99, ("yearly", "latam"): 19.99}
    assert plans["lifetime"]["saveLimit"] is None


def test_free_plan_stops_saving_at_the_limit():
    headers = auth_headers()
    for index in range(FREE_SAVE_LIMIT):
        assert save(headers, f"P{index}").status_code == 201

    blocked = save(headers)
    assert blocked.status_code == 402
    assert "Pro" in blocked.json()["detail"]
    subscription = client.get("/api/v1/billing/subscription", headers=headers).json()
    assert subscription["plan"] == "free" and subscription["saved"] == FREE_SAVE_LIMIT and subscription["saveLimit"] == FREE_SAVE_LIMIT


def test_mock_checkout_activates_pro_and_lifts_the_limit(repository):
    headers = auth_headers(uid="payer-uid")
    for index in range(FREE_SAVE_LIMIT):
        save(headers, f"P{index}")

    response = client.post("/api/v1/billing/checkout", json={"plan": "pro", "period": "yearly", "region": "latam"}, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock" and body["activated"] is True and body["checkoutUrl"] is None
    assert body["subscription"]["plan"] == "pro" and body["subscription"]["period"] == "yearly"
    assert body["subscription"]["renewsAt"] is not None and body["subscription"]["saveLimit"] is None
    assert repository.users["payer-uid"].plan_provider == "mock"
    assert client.get("/api/v1/auth/me", headers=headers).json()["plan"] == "pro"
    assert save(headers, "Sexta").status_code == 201


def test_lifetime_has_no_renewal_and_wrong_periods_are_rejected():
    headers = auth_headers()

    wrong = client.post("/api/v1/billing/checkout", json={"plan": "lifetime", "period": "monthly"}, headers=headers)
    assert wrong.status_code == 400
    free_plan = client.post("/api/v1/billing/checkout", json={"plan": "free", "period": "once"}, headers=headers)
    assert free_plan.status_code == 422

    lifetime = client.post("/api/v1/billing/checkout", json={"plan": "lifetime", "period": "once"}, headers=headers).json()
    assert lifetime["subscription"]["plan"] == "lifetime" and lifetime["subscription"]["renewsAt"] is None


def test_cancel_returns_to_free_and_keeps_saved_progressions():
    headers = auth_headers()
    client.post("/api/v1/billing/checkout", json={"plan": "pro", "period": "monthly"}, headers=headers)
    for index in range(FREE_SAVE_LIMIT + 2):
        save(headers, f"P{index}")

    cancelled = client.post("/api/v1/billing/cancel", headers=headers)

    assert cancelled.status_code == 200
    assert cancelled.json()["plan"] == "free" and cancelled.json()["saved"] == FREE_SAVE_LIMIT + 2
    assert save(headers).status_code == 402
    assert client.post("/api/v1/billing/cancel", headers=headers).status_code == 400


def test_billing_requires_login():
    assert client.get("/api/v1/billing/subscription").status_code == 401
    assert client.post("/api/v1/billing/checkout", json={"plan": "pro", "period": "monthly"}).status_code == 401
