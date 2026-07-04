from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_placeholder_media_is_served():
    resp = client.get("/media/placeholder.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


def test_missing_media_returns_404():
    resp = client.get("/media/does-not-exist.png")
    assert resp.status_code == 404
