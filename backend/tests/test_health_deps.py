from fastapi.testclient import TestClient

from app.main import app
from app.routers import health

client = TestClient(app)


def test_health_reports_dependency_status():
    resp = client.get("/health")
    body = resp.json()
    assert set(body.keys()) == {"status", "database", "redis"}
    assert body == {"status": "ok", "database": "ok", "redis": "ok"}


def test_health_reports_database_down(monkeypatch):
    class _BrokenEngine:
        def connect(self):
            raise RuntimeError("db connection failed")

    monkeypatch.setattr(health, "engine", _BrokenEngine())

    resp = client.get("/health")
    body = resp.json()

    assert resp.status_code == 503
    assert body["status"] == "degraded"
    assert body["database"] == "error"
    assert body["redis"] == "ok"


def test_health_reports_redis_down(monkeypatch):
    class _BrokenRedis:
        def ping(self):
            raise RuntimeError("redis connection failed")

    monkeypatch.setattr(health, "get_redis", lambda: _BrokenRedis())

    resp = client.get("/health")
    body = resp.json()

    assert resp.status_code == 503
    assert body["status"] == "degraded"
    assert body["redis"] == "error"
    assert body["database"] == "ok"
