def test_me_requires_authentication(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user_after_login(client):
    client.post(
        "/auth/register", json={"email": "me@example.com", "password": "password123"}
    )
    client.post(
        "/auth/login", json={"email": "me@example.com", "password": "password123"}
    )
    resp = client.get("/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "me@example.com"


def test_me_unauthorized_after_logout(client):
    client.post(
        "/auth/register", json={"email": "out@example.com", "password": "password123"}
    )
    client.post(
        "/auth/login", json={"email": "out@example.com", "password": "password123"}
    )
    assert client.get("/auth/me").status_code == 200
    client.post("/auth/logout")
    assert client.get("/auth/me").status_code == 401


def test_me_rejects_bogus_cookie(client):
    client.cookies.set("session", "totally-made-up-token")
    resp = client.get("/auth/me")
    assert resp.status_code == 401
