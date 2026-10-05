from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register(email: str | None = None) -> dict[str, str]:
    email = email or f"user-{uuid4().hex[:8]}@example.com"
    response = client.post("/api/v1/auth/register", json={"email": email, "password": "strong-password"})
    assert response.status_code == 201
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


def test_openapi_exposes_swagger_contract():
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    for path in (
        "/api/v1/chords",
        "/api/v1/chords/parse",
        "/api/v1/explore",
        "/api/v1/analyze",
        "/api/v1/tablature",
        "/api/v1/auth/register",
        "/api/v1/auth/me",
        "/api/v1/progressions/{progression_id}",
    ):
        assert path in paths


def test_list_chords_returns_catalog_with_extended_qualities():
    response = client.get("/api/v1/chords")

    assert response.status_code == 200
    chords = {chord["id"]: chord for chord in response.json()}
    assert len(chords) == 192
    assert chords["G7"]["notes"] == ["G", "B", "D", "F"]
    assert chords["G7"]["triad"] == ["G", "B", "D"]
    assert "Am7" in chords and "Dsus4" in chords and "E5" in chords


def test_get_chord_accepts_flats_and_latin_names():
    assert client.get("/api/v1/chords/Bb").json()["id"] == "A#"
    assert client.get("/api/v1/chords/SOLm").json()["id"] == "Gm"
    assert client.get("/api/v1/chords/H").status_code == 404


def test_parse_endpoint_reports_each_symbol():
    response = client.post("/api/v1/chords/parse", json={"symbols": ["D/F#", "Fmaj9", "N.C."]})

    assert response.status_code == 200
    results = response.json()["results"]
    assert results[0] == {"input": "D/F#", "chord": "D", "bass": "F#", "approximated": False, "error": None}
    assert results[1]["chord"] == "Fmaj7" and results[1]["approximated"] is True
    assert results[2]["chord"] is None and results[2]["error"]


def test_get_connections_returns_scored_edges():
    response = client.get("/api/v1/chords/G7/connections", params={"tonality": "C"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "G7"
    assert payload["total"] > 0
    assert payload["connections"][0]["target"].startswith("C")


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
    response = client.post("/api/v1/analyze", json={"chords": ["C", "G7", "C"], "tonality": "C"})

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["chords"] == ["C", "G7", "C"]
    assert len(analysis["connections"]) == 2
    assert analysis["tensionCurve"][0]["from"] == "C"
    assert analysis["key"] == {"id": "C", "label": "Do mayor (C)", "mode": "major", "confidence": 1.0, "detected": False}
    assert [degree["numeral"] for degree in analysis["degrees"]] == ["I", "V7", "I"]
    assert analysis["suggestions"]


def test_analyze_detects_key_from_song_chords():
    response = client.post("/api/v1/analyze", json={"chords": ["Bm", "G", "D", "A"]})

    assert response.status_code == 200
    analysis = response.json()["analysis"]
    assert analysis["key"]["id"] == "Bm"
    assert analysis["key"]["detected"] is True
    assert [degree["numeral"] for degree in analysis["degrees"]] == ["i", "VI", "III", "VII"]
    assert all(degree["substitutions"] for degree in analysis["degrees"])


def test_analyze_rejects_unknown_chord():
    response = client.post("/api/v1/analyze", json={"chords": ["C", "H"]})

    assert response.status_code == 400


def test_generate_tablature_returns_text_lines():
    response = client.post("/api/v1/tablature", json={"title": "Demo", "chords": ["C", "G7", "Am"]})

    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Demo"
    assert payload["chords"] == ["C", "G7", "Am"]
    assert len(payload["lines"]) == 6
    assert len(payload["arpeggioLines"]) == 6
    assert "e|" in payload["text"]
    arpeggio_text = payload["text"].split("Arpegio sugerido (solo cuerda y traste):", 1)[1]
    assert "G7" not in arpeggio_text
    assert payload["diagrams"][0]["frets"] == ["0", "1", "0", "2", "3", "x"]


def test_generate_tablature_accepts_extended_chords():
    response = client.post("/api/v1/tablature", json={"chords": ["Am7", "Bbmaj7", "D/F#"]})

    assert response.status_code == 200
    assert response.json()["chords"] == ["Am7", "A#maj7", "D"]


def test_generate_tablature_rejects_unknown_chord():
    response = client.post("/api/v1/tablature", json={"chords": ["C", "H"]})

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown chord: H"


def test_progressions_require_login():
    assert client.get("/api/v1/progressions").status_code == 401
    assert client.post("/api/v1/progressions", json={"name": "x", "chords": ["C"]}).status_code == 401


def test_progressions_crud_roundtrip():
    headers = register()
    create_response = client.post(
        "/api/v1/progressions",
        json={"name": "Cadencia", "chords": ["C", "G7", "C"], "tonality": "C"},
        headers=headers,
    )
    assert create_response.status_code == 201
    progression = create_response.json()
    assert progression["isOwner"] is True

    get_response = client.get(f"/api/v1/progressions/{progression['id']}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Cadencia"

    update_response = client.put(
        f"/api/v1/progressions/{progression['id']}",
        json={"name": "Cadencia final", "chords": ["C", "F", "G7", "Bb"]},
        headers=headers,
    )
    assert update_response.status_code == 200
    assert update_response.json()["chords"] == ["C", "F", "G7", "A#"]

    list_response = client.get("/api/v1/progressions", headers=headers)
    assert list_response.json()["total"] == 1

    assert client.delete(f"/api/v1/progressions/{progression['id']}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/progressions/{progression['id']}", headers=headers).status_code == 404


def test_progressions_are_private_unless_shared():
    owner = register()
    other = register()
    progression = client.post(
        "/api/v1/progressions", json={"name": "Mía", "chords": ["Am", "F"]}, headers=owner
    ).json()
    url = f"/api/v1/progressions/{progression['id']}"

    assert client.get(url).status_code == 404
    assert client.get(url, headers=other).status_code == 404
    assert client.get("/api/v1/progressions", headers=other).json()["total"] == 0
    assert client.delete(url, headers=other).status_code == 404

    client.put(url, json={"isPublic": True}, headers=owner)
    shared = client.get(url)
    assert shared.status_code == 200
    assert shared.json()["isOwner"] is False


def test_progression_rejects_unknown_chord():
    response = client.post(
        "/api/v1/progressions", json={"name": "Invalid", "chords": ["C", "H"]}, headers=register()
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown chord: H"


def test_auth_register_login_and_me():
    email = f"auth-{uuid4().hex[:8]}@example.com"
    register_response = client.post(
        "/api/v1/auth/register", json={"email": email, "password": "strong-password", "displayName": "Gus"}
    )
    assert register_response.status_code == 201
    assert register_response.json()["user"]["displayName"] == "Gus"

    duplicate = client.post("/api/v1/auth/register", json={"email": email.upper(), "password": "strong-password"})
    assert duplicate.status_code == 409

    login_response = client.post("/api/v1/auth/login", json={"email": email, "password": "strong-password"})
    assert login_response.status_code == 200
    token = login_response.json()["accessToken"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["email"] == email


def test_auth_login_rejects_invalid_credentials():
    response = client.post(
        "/api/v1/auth/login", json={"email": "missing@example.com", "password": "strong-password"}
    )

    assert response.status_code == 401


def test_invalid_token_is_rejected():
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"})

    assert response.status_code == 401
