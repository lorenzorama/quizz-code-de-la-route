import openpyxl

from app.importer import REQUIRED_COLUMNS


def write_workbook(path, rows: list[dict]):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(REQUIRED_COLUMNS)
    for row in rows:
        ws.append([row.get(col, "") for col in REQUIRED_COLUMNS])
    wb.save(path)
    return str(path)


def valid_row(ref="Q001", correct="B", **overrides):
    row = {
        "ref": ref,
        "theme": "priorités",
        "question_text": "Qui passe en premier ?",
        "option_a": "Moi",
        "option_b": "Le véhicule de droite",
        "option_c": "Le piéton",
        "option_d": "Personne",
        "correct": correct,
        "explanation": "Priorité à droite.",
        "media_path": "placeholder.png",
        "media_type": "image",
    }
    row.update(overrides)
    return row


def seed_questions(session, n, correct_label="A"):
    from app.models import Option, Question

    questions = []
    for i in range(n):
        question = Question(
            ref=f"E{i:03d}",
            theme="theme",
            text=f"Question {i}?",
            media_type="none",
            explanation=f"Explanation {i}",
        )
        question.options = [
            Option(label=label, text=f"Option {label}", is_correct=(label == correct_label))
            for label in ["A", "B", "C", "D"]
        ]
        session.add(question)
        questions.append(question)
    session.flush()
    return questions
