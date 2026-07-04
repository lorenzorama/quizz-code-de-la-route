from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_root_returns_service_name():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "quizz-code-de-la-route"
