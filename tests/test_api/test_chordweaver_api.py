from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_openapi_exposes_swagger_contract():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/chords" in paths
    assert "/api/v1/explore" in paths
    assert "/api/v1/analyze" in paths
    assert "/api/v1/tablature" in paths
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/progressions/{progression_id}" in paths


def test_list_chords_returns_catalog():
    response = client.get("/api/v1/chords")

    assert response.status_code == 200
    chords = response.json()
    assert len(chords) == 72
    assert any(chord["id"] == "C" for chord in chords)
    assert any(chord["id"] == "G7" for chord in chords)


def test_get_connections_returns_scored_edges():
    response = client.get("/api/v1/chords/G7/connections", params={"tonality": "C"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "G7"
    assert payload["total"] > 0
    assert any(connection["target"] == "C" for connection in payload["connections"])


def test_explore_filters_by_preferred_tension():
    response = client.post(
        "/api/v1/explore",
        json={"currentChord": "C", "preferredTension": "natural", "maxResults": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["currentChord"] == "C"
    assert payload["total"] <= 5
    assert all(item["category"] == "natural" for item in payload["suggestions"])


def test_analyze_returns_connections_and_tension_curve():
    response = client.post(
        "/api/v1/analyze",
        json={"chords": ["C", "G7", "C"], "tonality": "C"},
    )

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["chords"] == ["C", "G7", "C"]
    assert len(analysis["connections"]) == 2
    assert len(analysis["tensionCurve"]) == 2
    assert "suggestions" in analysis


def test_generate_tablature_returns_text_lines():
    response = client.post(
        "/api/v1/tablature",
        json={"title": "Demo", "chords": ["C", "G7", "Am"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Demo"
    assert payload["chords"] == ["C", "G7", "Am"]
    assert len(payload["lines"]) == 6
    assert len(payload["arpeggioLines"]) == 6
    assert "e|" in payload["text"]
    assert "Arpegio sugerido (solo cuerda y traste)" in payload["text"]
    arpeggio_text = payload["text"].split("Arpegio sugerido (solo cuerda y traste):", 1)[1]
    assert "G7" not in arpeggio_text
    assert "Am" not in arpeggio_text
    assert payload["diagrams"][0]["frets"] == ["0", "1", "0", "2", "3", "x"]


def test_generate_tablature_rejects_unknown_chord():
    response = client.post(
        "/api/v1/tablature",
        json={"chords": ["C", "H"]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown chord: H"


def test_progressions_crud_roundtrip():
    create_response = client.post(
        "/api/v1/progressions",
        json={"name": "Cadencia", "chords": ["C", "G7", "C"], "tonality": "C"},
    )
    assert create_response.status_code == 201
    progression = create_response.json()

    get_response = client.get(f"/api/v1/progressions/{progression['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Cadencia"

    update_response = client.put(
        f"/api/v1/progressions/{progression['id']}",
        json={"name": "Cadencia final", "chords": ["C", "F", "G7", "C"]},
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Cadencia final"
    assert update_response.json()["chords"] == ["C", "F", "G7", "C"]

    list_response = client.get("/api/v1/progressions")
    assert list_response.status_code == 200
    assert list_response.json()["total"] >= 1

    delete_response = client.delete(f"/api/v1/progressions/{progression['id']}")
    assert delete_response.status_code == 204

    missing_response = client.get(f"/api/v1/progressions/{progression['id']}")
    assert missing_response.status_code == 404


def test_progression_rejects_unknown_chord():
    response = client.post(
        "/api/v1/progressions",
        json={"name": "Invalid", "chords": ["C", "H"]},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown chord: H"


def test_auth_register_and_login_returns_jwt():
    email = "test-auth@example.com"
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strong-password"},
    )
    assert register_response.status_code == 201
    assert register_response.json()["tokenType"] == "bearer"
    assert register_response.json()["accessToken"]

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "strong-password"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["accessToken"]


def test_auth_login_rejects_invalid_credentials():
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "strong-password"},
    )

    assert response.status_code == 401
