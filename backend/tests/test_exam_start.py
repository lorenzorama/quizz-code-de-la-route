from tests.helpers import seed_questions


def _register_and_login(client, email="exam@example.com"):
    client.post("/auth/register", json={"email": email, "password": "password123"})
    client.post("/auth/login", json={"email": email, "password": "password123"})


def test_start_requires_authentication(client):
    resp = client.post("/exam/start")
    assert resp.status_code == 401


def test_start_returns_requested_number_of_questions(client, session):
    seed_questions(session, 40)
    _register_and_login(client)
    resp = client.post("/exam/start")
    assert resp.status_code == 201
    body = resp.json()
    assert body["question_count"] == 40
    assert len(body["questions"]) == 40
    assert "attempt_id" in body


def test_start_caps_at_available_questions(client, session):
    seed_questions(session, 5)
    _register_and_login(client)
    resp = client.post("/exam/start")
    assert resp.status_code == 201
    assert resp.json()["question_count"] == 5


def test_start_does_not_leak_answer_keys(client, session):
    seed_questions(session, 40)
    _register_and_login(client)
    body = client.post("/exam/start").json()
    serialized = str(body)
    assert "is_correct" not in serialized
    assert "explanation" not in serialized
    for question in body["questions"]:
        for option in question["options"]:
            assert set(option.keys()) == {"id", "label", "text"}


def test_start_with_no_questions_conflicts(client, session):
    _register_and_login(client)
    resp = client.post("/exam/start")
    assert resp.status_code == 409
