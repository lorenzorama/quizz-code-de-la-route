from app.models import Option, Question


def _seed(session, ref, theme, correct="A"):
    q = Question(
        ref=ref, theme=theme, text=f"Q {ref}", media_type="none", explanation=f"Expl {ref}"
    )
    q.options = [
        Option(label=label, text=label, is_correct=(label == correct))
        for label in ["A", "B", "C", "D"]
    ]
    session.add(q)
    session.flush()
    return q


def _login(client, email="practice@example.com"):
    client.post("/auth/register", json={"email": email, "password": "password123"})
    client.post("/auth/login", json={"email": email, "password": "password123"})


def test_themes_requires_auth(client):
    assert client.get("/practice/themes").status_code == 401


def test_themes_lists_counts(client, session):
    _seed(session, "P1", "panneaux")
    _seed(session, "P2", "panneaux")
    _seed(session, "V1", "vitesse")
    _login(client)
    resp = client.get("/practice/themes")
    assert resp.status_code == 200
    data = {t["theme"]: t["count"] for t in resp.json()}
    assert data == {"panneaux": 2, "vitesse": 1}


def test_questions_filters_by_theme_and_exposes_answers(client, session):
    _seed(session, "P1", "panneaux", correct="B")
    _seed(session, "V1", "vitesse")
    _login(client)
    resp = client.get("/practice/questions", params={"theme": ["panneaux"]})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    q = body[0]
    assert q["theme"] == "panneaux"
    assert q["explanation"] == "Expl P1"
    assert [o["label"] for o in q["options"] if o["is_correct"]] == ["B"]


def test_questions_accepts_multiple_themes(client, session):
    _seed(session, "P1", "panneaux")
    _seed(session, "V1", "vitesse")
    _seed(session, "PR1", "priorités")
    _login(client)
    resp = client.get(
        "/practice/questions", params={"theme": ["panneaux", "vitesse"]}
    )
    assert resp.status_code == 200
    assert {q["theme"] for q in resp.json()} == {"panneaux", "vitesse"}
    assert len(resp.json()) == 2


def test_questions_no_theme_returns_empty(client, session):
    _seed(session, "P1", "panneaux")
    _login(client)
    assert client.get("/practice/questions").json() == []


def test_questions_requires_auth(client):
    assert client.get("/practice/questions", params={"theme": ["x"]}).status_code == 401
