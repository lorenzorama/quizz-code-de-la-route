from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_dependency_status():
    resp = client.get("/health")
    body = resp.json()
    assert set(body.keys()) == {"status", "database", "redis"}
    assert body["database"] in {"ok", "error"}
    assert body["redis"] in {"ok", "error"}
