from tests.helpers import seed_questions


def _register_and_login(client, email="history@example.com"):
    client.post("/auth/register", json={"email": email, "password": "password123"})
    client.post("/auth/login", json={"email": email, "password": "password123"})


def test_history_lists_users_attempts_newest_first(client, session):
    seed_questions(session, 3)
    _register_and_login(client)
    id1 = client.post("/exam/start").json()["attempt_id"]
    id2 = client.post("/exam/start").json()["attempt_id"]

    resp = client.get("/exam/history")
    assert resp.status_code == 200
    body = resp.json()
    ids = [a["id"] for a in body]
    assert id1 in ids and id2 in ids
    # newest-first: id2 started at or after id1, so it should not come after id1
    assert ids.index(id2) <= ids.index(id1)
    assert body[0]["status"] in {"in_progress", "completed"}


def test_history_excludes_other_users_attempts(client, session):
    seed_questions(session, 3)
    _register_and_login(client, email="mine@example.com")
    my_id = client.post("/exam/start").json()["attempt_id"]
    client.post("/auth/logout")
    _register_and_login(client, email="other@example.com")

    resp = client.get("/exam/history")
    assert resp.status_code == 200
    assert all(a["id"] != my_id for a in resp.json())


def test_history_requires_authentication(client):
    resp = client.get("/exam/history")
    assert resp.status_code == 401
