from sqlalchemy import func, select

from app.importer import import_questions, parse_workbook
from app.models import Option, Question
from tests.helpers import valid_row, write_workbook


def test_import_creates_questions_and_options(session, tmp_path):
    rows = parse_workbook(
        write_workbook(tmp_path / "q.xlsx", [valid_row(ref="Q001", correct="A,C")])
    )
    stats = import_questions(session, rows)
    assert stats == {"created": 1, "updated": 0}

    question = session.scalar(select(Question).where(Question.ref == "Q001"))
    assert question is not None
    assert len(question.options) == 4
    correct = {o.label for o in question.options if o.is_correct}
    assert correct == {"A", "C"}


def test_reimport_is_idempotent(session, tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(ref="Q001")])
    import_questions(session, parse_workbook(path))
    stats = import_questions(session, parse_workbook(path))

    assert stats == {"created": 0, "updated": 1}
    assert session.scalar(select(func.count()).select_from(Question)) == 1
    assert session.scalar(select(func.count()).select_from(Option)) == 4


def test_reimport_updates_changed_fields(session, tmp_path):
    import_questions(
        session,
        parse_workbook(write_workbook(tmp_path / "a.xlsx", [valid_row(ref="Q001", correct="A")])),
    )
    import_questions(
        session,
        parse_workbook(
            write_workbook(
                tmp_path / "b.xlsx",
                [valid_row(ref="Q001", correct="B", question_text="Nouvelle question ?")],
            )
        ),
    )
    question = session.scalar(select(Question).where(Question.ref == "Q001"))
    assert question.text == "Nouvelle question ?"
    assert {o.label for o in question.options if o.is_correct} == {"B"}
