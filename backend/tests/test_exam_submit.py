import math

from app.config import settings
from tests.helpers import seed_questions


def _register_and_login(client, email="submit@example.com"):
    client.post("/auth/register", json={"email": email, "password": "password123"})
    client.post("/auth/login", json={"email": email, "password": "password123"})


def _correct_answers(questions):
    return [
        {
            "question_id": q.id,
            "selected_option_ids": [o.id for o in q.options if o.is_correct],
        }
        for q in questions
    ]


def _wrong_answers(questions):
    return [
        {
            "question_id": q.id,
            "selected_option_ids": [o.id for o in q.options if not o.is_correct][:1],
        }
        for q in questions
    ]


def test_all_correct_scores_full_and_passes(client, session):
    questions = seed_questions(session, 40)
    _register_and_login(client)
    attempt_id = client.post("/exam/start").json()["attempt_id"]
    resp = client.post(
        f"/exam/{attempt_id}/submit", json={"answers": _correct_answers(questions)}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["score"] == 40
    assert body["total"] == 40
    assert body["passed"] is True


def test_pass_threshold_boundary(client, session):
    questions = seed_questions(session, 40)
    _register_and_login(client)
    attempt_id = client.post("/exam/start").json()["attempt_id"]
    required = math.ceil(settings.pass_ratio * 40)
    answers = _correct_answers(questions[:required]) + _wrong_answers(
        questions[required:]
    )
    body = client.post(f"/exam/{attempt_id}/submit", json={"answers": answers}).json()
    assert body["score"] == required
    assert body["passed"] is True


def test_one_below_threshold_fails(client, session):
    questions = seed_questions(session, 40)
    _register_and_login(client)
    attempt_id = client.post("/exam/start").json()["attempt_id"]
    required = math.ceil(settings.pass_ratio * 40)
    n = required - 1
    answers = _correct_answers(questions[:n]) + _wrong_answers(questions[n:])
    body = client.post(f"/exam/{attempt_id}/submit", json={"answers": answers}).json()
    assert body["score"] == n
    assert body["passed"] is False


def test_small_bank_perfect_score_passes(client, session):
    questions = seed_questions(session, 4)
    _register_and_login(client)
    attempt_id = client.post("/exam/start").json()["attempt_id"]
    body = client.post(
        f"/exam/{attempt_id}/submit", json={"answers": _correct_answers(questions)}
    ).json()
    assert body["score"] == 4
    assert body["total"] == 4
    assert body["passed"] is True


def test_submit_ignores_unknown_question_id(client, session):
    questions = seed_questions(session, 3)
    _register_and_login(client)
    attempt_id = client.post("/exam/start").json()["attempt_id"]
    answers = _correct_answers(questions) + [
        {"question_id": 999999, "selected_option_ids": [123456]}
    ]
    resp = client.post(f"/exam/{attempt_id}/submit", json={"answers": answers})
    assert resp.status_code == 200
    assert resp.json()["score"] == 3


def test_unsubmitted_questions_count_wrong(client, session):
    questions = seed_questions(session, 10)
    _register_and_login(client)
    attempt_id = client.post("/exam/start").json()["attempt_id"]
    answers = _correct_answers(questions[:3])  # only 3 of 10 submitted
    body = client.post(f"/exam/{attempt_id}/submit", json={"answers": answers}).json()
    assert body["score"] == 3
    assert body["total"] == 10


def test_double_submit_conflicts(client, session):
    questions = seed_questions(session, 5)
    _register_and_login(client)
    attempt_id = client.post("/exam/start").json()["attempt_id"]
    client.post(f"/exam/{attempt_id}/submit", json={"answers": _correct_answers(questions)})
    resp = client.post(
        f"/exam/{attempt_id}/submit", json={"answers": _correct_answers(questions)}
    )
    assert resp.status_code == 409


def test_submit_other_users_attempt_not_found(client, session):
    questions = seed_questions(session, 5)
    _register_and_login(client, email="owner@example.com")
    attempt_id = client.post("/exam/start").json()["attempt_id"]
    # switch to a different user on the same client
    client.post("/auth/logout")
    _register_and_login(client, email="intruder@example.com")
    resp = client.post(
        f"/exam/{attempt_id}/submit", json={"answers": _correct_answers(questions)}
    )
    assert resp.status_code == 404


def test_submit_requires_authentication(client, session):
    resp = client.post("/exam/1/submit", json={"answers": []})
    assert resp.status_code == 401
