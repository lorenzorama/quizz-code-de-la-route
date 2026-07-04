import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Attempt, AttemptAnswer, Option, Question, User


def test_can_persist_user(session):
    user = User(email="a@b.com", password_hash="x")
    session.add(user)
    session.flush()
    assert user.id is not None
    assert user.created_at is not None


def test_question_with_options_cascade(session):
    q = Question(ref="Q001", theme="priorités", text="Qui passe ?")
    q.options = [
        Option(label="A", text="Moi", is_correct=False),
        Option(label="B", text="Le véhicule de droite", is_correct=True),
    ]
    session.add(q)
    session.flush()
    assert len(q.options) == 2
    assert {o.label for o in q.options} == {"A", "B"}


def test_attempt_answer_stores_selected_ids(session):
    user = User(email="c@d.com", password_hash="x")
    question = Question(ref="Q002", theme="priorités", text="Qui passe ?")
    session.add_all([user, question])
    session.flush()
    attempt = Attempt(user_id=user.id, status="in_progress")
    attempt.answers = [
        AttemptAnswer(
            question_id=question.id, selected_option_ids=[10, 11], is_correct=True
        )
    ]
    session.add(attempt)
    session.flush()
    assert attempt.answers[0].selected_option_ids == [10, 11]
    assert attempt.status == "in_progress"


def test_option_label_unique_per_question(session):
    q = Question(ref="Q003", theme="priorités", text="Qui passe ?")
    q.options = [Option(label="A", text="Moi", is_correct=False)]
    session.add(q)
    session.flush()

    session.add(Option(question_id=q.id, label="A", text="Doublon", is_correct=False))
    with pytest.raises(IntegrityError):
        session.flush()
