from app.config import settings
from app.sessions import get_session_user_id


def test_register_creates_user(client):
    resp = client.post(
        "/auth/register", json={"email": "a@example.com", "password": "password123"}
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert "id" in body
    assert "password" not in body and "password_hash" not in body


def test_register_duplicate_email_conflicts(client):
    payload = {"email": "dup@example.com", "password": "password123"}
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def test_register_rejects_short_password(client):
    resp = client.post(
        "/auth/register", json={"email": "b@example.com", "password": "short"}
    )
    assert resp.status_code == 422


def test_register_rejects_invalid_email(client):
    resp = client.post(
        "/auth/register", json={"email": "not-an-email", "password": "password123"}
    )
    assert resp.status_code == 422


def test_login_succeeds_and_sets_cookie(client):
    client.post(
        "/auth/register", json={"email": "c@example.com", "password": "password123"}
    )
    resp = client.post(
        "/auth/login", json={"email": "c@example.com", "password": "password123"}
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "c@example.com"
    assert settings.session_cookie_name in resp.cookies


def test_login_wrong_password_unauthorized(client):
    client.post(
        "/auth/register", json={"email": "d@example.com", "password": "password123"}
    )
    resp = client.post(
        "/auth/login", json={"email": "d@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401
    assert settings.session_cookie_name not in resp.cookies


def test_login_cookie_has_security_attributes(client):
    client.post(
        "/auth/register", json={"email": "f@example.com", "password": "password123"}
    )
    resp = client.post(
        "/auth/login", json={"email": "f@example.com", "password": "password123"}
    )
    assert resp.status_code == 200
    set_cookie = resp.headers["set-cookie"].lower()
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert f"max-age={settings.session_ttl_seconds}" in set_cookie
    assert "secure" not in set_cookie


def test_login_unknown_email_unauthorized(client):
    resp = client.post(
        "/auth/login", json={"email": "nobody@example.com", "password": "password123"}
    )
    assert resp.status_code == 401


def test_logout_returns_204(client):
    client.post(
        "/auth/register", json={"email": "e@example.com", "password": "password123"}
    )
    client.post(
        "/auth/login", json={"email": "e@example.com", "password": "password123"}
    )
    resp = client.post("/auth/logout")
    assert resp.status_code == 204


def test_logout_deletes_redis_session(client):
    client.post(
        "/auth/register", json={"email": "g@example.com", "password": "password123"}
    )
    resp = client.post(
        "/auth/login", json={"email": "g@example.com", "password": "password123"}
    )
    user_id = resp.json()["id"]
    token = client.cookies.get(settings.session_cookie_name)

    assert get_session_user_id(token) == user_id

    logout_resp = client.post("/auth/logout")
    assert logout_resp.status_code == 204

    assert get_session_user_id(token) is None
