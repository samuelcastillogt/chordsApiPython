from fastapi.testclient import TestClient

from app.main import app
from tests.firebase_fakes import auth_headers

client = TestClient(app)


def test_share_page_has_preview_tags_and_redirects_to_the_explorer():
    headers = auth_headers()
    progression = client.post(
        "/api/v1/progressions",
        json={"name": "Té para <tres>", "chords": ["Bm", "G", "D", "A"], "tonality": "Bm", "isPublic": True},
        headers=headers,
    ).json()

    response = client.get(f"/p/{progression['id']}")

    assert response.status_code == 200
    html = response.text
    assert '<meta property="og:title" content="Té para &lt;tres&gt; · ChordWeaver">' in html
    assert "Bm – G – D – A en Bm" in html
    assert f"/explorer/?p={progression['id']}" in html
    assert "<tres>" not in html


def test_private_or_missing_progressions_are_not_previewed():
    headers = auth_headers()
    private = client.post("/api/v1/progressions", json={"name": "Secreta", "chords": ["C"]}, headers=headers).json()

    for path in (f"/p/{private['id']}", "/p/no-existe"):
        response = client.get(path)
        assert response.status_code == 404
        assert "Secreta" not in response.text
