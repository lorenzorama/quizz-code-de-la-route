from tests.helpers import seed_questions


def _register_and_login(client, email="review@example.com"):
    client.post("/auth/register", json={"email": email, "password": "password123"})
    client.post("/auth/login", json={"email": email, "password": "password123"})


def _correct_answers(questions):
    return [
        {"question_id": q.id, "selected_option_ids": [o.id for o in q.options if o.is_correct]}
        for q in questions
    ]


def test_review_shows_answers_explanations_and_selections(client, session):
    questions = seed_questions(session, 3)
    _register_and_login(client)
    attempt_id = client.post("/exam/start").json()["attempt_id"]
    client.post(f"/exam/{attempt_id}/submit", json={"answers": _correct_answers(questions)})

    resp = client.get(f"/exam/{attempt_id}/review")
    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] == 3
    assert len(body["questions"]) == 3
    first = body["questions"][0]
    assert "explanation" in first and first["explanation"]
    assert any(o["is_correct"] for o in first["options"])
    assert first["is_correct"] is True
    assert first["selected_option_ids"]


def test_review_of_in_progress_attempt_conflicts(client, session):
    seed_questions(session, 3)
    _register_and_login(client)
    attempt_id = client.post("/exam/start").json()["attempt_id"]
    resp = client.get(f"/exam/{attempt_id}/review")
    assert resp.status_code == 409


def test_review_other_users_attempt_not_found(client, session):
    questions = seed_questions(session, 3)
    _register_and_login(client, email="owner2@example.com")
    attempt_id = client.post("/exam/start").json()["attempt_id"]
    client.post(f"/exam/{attempt_id}/submit", json={"answers": _correct_answers(questions)})
    client.post("/auth/logout")
    _register_and_login(client, email="intruder2@example.com")
    resp = client.get(f"/exam/{attempt_id}/review")
    assert resp.status_code == 404


def test_review_requires_authentication(client, session):
    resp = client.get("/exam/1/review")
    assert resp.status_code == 401
