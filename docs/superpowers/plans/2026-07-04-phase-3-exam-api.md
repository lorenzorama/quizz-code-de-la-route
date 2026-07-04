# Phase 3 — Exam API Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the timed exam-simulation API: start an attempt (40 random questions, no answer keys leaked), submit answers and score server-side (all-or-nothing multi-select, pass at 35/40), review a completed attempt with explanations + media, and list attempt history — all scoped to the logged-in user.

**Architecture:** Scoring is a pure function in `app/scoring.py` (`is_answer_correct`), independent of HTTP/DB, so it can be tested exhaustively. Exam request/response shapes live in `app/exam_schemas.py`; the `/exam` endpoints live in `app/routers/exam.py`, protected by the Phase 2 `get_current_user` dependency and using `Depends(get_session)`. An attempt's 40 questions are recorded durably as `attempt_answers` rows at start time (empty selection), which submit fills in and review reads. A one-line ORM relationship (`AttemptAnswer.question`) is added — no migration (no schema change).

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Postgres, pytest. Builds on Phase 1 (models, DB) and Phase 2 (auth dependency, test isolation).

## Global Constraints

- Run all commands from `backend/` with the venv active (`. .venv/bin/activate`); Postgres + Redis up (`docker compose up -d postgres redis`).
- All `/exam` endpoints require authentication via `Depends(get_current_user)` (Phase 2). Ownership is enforced: an attempt not owned by the current user returns **404** (never reveal existence).
- **Mutating endpoints are POST** (never GET) — preserves the Phase 2 SameSite/CSRF posture. Read endpoints are GET.
- Endpoints use `Depends(get_session)` for DB access (never `SessionLocal()` directly) so test isolation holds.
- **Scoring** is the pure function `is_answer_correct(correct_option_ids: set[int], selected_option_ids: set[int]) -> bool`: a point only when the selected set **exactly equals** the non-empty correct set (all correct chosen, none incorrect). Empty selection scores wrong.
- **Start** returns questions WITHOUT `is_correct` flags and WITHOUT `explanation` (no answer leak via the network).
- Exam size and pass mark come from settings: `exam_question_count` (default 40), `pass_threshold` (default 35). Start selects `min(exam_question_count, available)` questions.
- Status codes: start → `201`; submit → `200` (`404` not owned/found, `409` already completed); review → `200` (`404` not owned/found, `409` not yet completed); history → `200`.
- SQLAlchemy 2.0 style; `datetime.now(timezone.utc)` for `finished_at`.
- The Redis question-pool cache mentioned in the spec is intentionally **deferred** (YAGNI at current bank size); assembly queries Postgres directly. Noted here so it is a conscious omission, not a gap.
- Every task ends with a passing test run and a commit.

---

### Task 1: Pure scoring function + exam settings

**Files:**
- Create: `backend/app/scoring.py`
- Modify: `backend/app/config.py`
- Create: `backend/tests/test_scoring.py`

**Interfaces:**
- Produces:
  - `app.scoring.is_answer_correct(correct_option_ids: set[int], selected_option_ids: set[int]) -> bool`.
  - `settings.exam_question_count: int` (default 40), `settings.pass_threshold: int` (default 35).

- [ ] **Step 1: Create `app/scoring.py`**

```python
def is_answer_correct(
    correct_option_ids: set[int], selected_option_ids: set[int]
) -> bool:
    """A question is correct only when the selected options exactly match the
    (non-empty) set of correct options — all correct chosen, none incorrect."""
    if not correct_option_ids:
        return False
    return selected_option_ids == correct_option_ids
```

- [ ] **Step 2: Add exam settings to `app/config.py`**

Add these two fields to the `Settings` class (alongside the existing fields):

```python
    exam_question_count: int = 40
    pass_threshold: int = 35
```

- [ ] **Step 3: Write the failing test — `tests/test_scoring.py`**

```python
from app.scoring import is_answer_correct


def test_single_correct_selected():
    assert is_answer_correct({1}, {1}) is True


def test_single_correct_wrong_option():
    assert is_answer_correct({1}, {2}) is False


def test_multi_correct_all_selected():
    assert is_answer_correct({1, 3}, {1, 3}) is True


def test_multi_correct_partial_selection_is_wrong():
    assert is_answer_correct({1, 3}, {1}) is False


def test_multi_correct_over_selection_is_wrong():
    assert is_answer_correct({1, 3}, {1, 3, 4}) is False


def test_empty_selection_is_wrong():
    assert is_answer_correct({1}, set()) is False


def test_selection_order_irrelevant():
    assert is_answer_correct({1, 2, 3}, {3, 2, 1}) is True


def test_empty_correct_set_is_wrong():
    assert is_answer_correct(set(), set()) is False
```

- [ ] **Step 4: Run the tests**

Run: `pytest tests/test_scoring.py -v`
Expected: 8 tests PASS. (Pure — no DB/redis needed.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/scoring.py backend/app/config.py backend/tests/test_scoring.py
git commit -m "feat(backend): add pure all-or-nothing scoring function and exam settings"
```

---

### Task 2: Exam schemas, `AttemptAnswer.question` relationship, and start endpoint

**Files:**
- Modify: `backend/app/models.py`
- Create: `backend/app/exam_schemas.py`
- Create: `backend/app/routers/exam.py`
- Modify: `backend/app/main.py`
- Modify: `backend/tests/helpers.py`
- Create: `backend/tests/test_exam_start.py`

**Interfaces:**
- Consumes: `get_current_user` (Phase 2), `get_session`, `settings.exam_question_count`, `Attempt`/`AttemptAnswer`/`Question`/`Option`/`User` models.
- Produces:
  - `AttemptAnswer.question` relationship (ORM-only, no migration).
  - `app.exam_schemas`: `ExamOptionOut`, `ExamQuestionOut`, `StartExamResponse`, `SubmittedAnswer`, `SubmitExamRequest`, `ExamResultOut`, `ReviewOptionOut`, `ReviewQuestionOut`, `ReviewOut`, `AttemptSummaryOut` (defined all at once; used across Tasks 2–4).
  - `/exam` router with `POST /exam/start`, wired into `app.main:app`.
  - `tests/helpers.py`: `seed_questions(session, n, correct_label="A")`.

- [ ] **Step 1: Add the `question` relationship to `AttemptAnswer` in `app/models.py`**

In the `AttemptAnswer` class, add this relationship (below the existing `attempt` relationship). This is ORM-only and needs no migration:

```python
    question: Mapped["Question"] = relationship()
```

- [ ] **Step 2: Create `app/exam_schemas.py`**

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ExamOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    text: str


class ExamQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    theme: str
    text: str
    media_path: str | None
    media_type: str
    options: list[ExamOptionOut]


class StartExamResponse(BaseModel):
    attempt_id: int
    question_count: int
    questions: list[ExamQuestionOut]


class SubmittedAnswer(BaseModel):
    question_id: int
    selected_option_ids: list[int] = []
    time_taken: int | None = None


class SubmitExamRequest(BaseModel):
    answers: list[SubmittedAnswer] = []


class ExamResultOut(BaseModel):
    attempt_id: int
    score: int
    total: int
    passed: bool


class ReviewOptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    text: str
    is_correct: bool


class ReviewQuestionOut(BaseModel):
    id: int
    theme: str
    text: str
    media_path: str | None
    media_type: str
    explanation: str
    options: list[ReviewOptionOut]
    selected_option_ids: list[int]
    is_correct: bool


class ReviewOut(BaseModel):
    attempt_id: int
    score: int
    total: int
    passed: bool
    questions: list[ReviewQuestionOut]


class AttemptSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: datetime | None
    score: int | None
    passed: bool | None
    status: str
```

- [ ] **Step 3: Create `app/routers/exam.py` (start endpoint only for now)**

```python
import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_session
from app.deps import get_current_user
from app.exam_schemas import ExamQuestionOut, StartExamResponse
from app.models import Attempt, AttemptAnswer, Question, User

router = APIRouter(prefix="/exam", tags=["exam"])


@router.post("/start", response_model=StartExamResponse, status_code=status.HTTP_201_CREATED)
def start_exam(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> StartExamResponse:
    all_ids = list(db.scalars(select(Question.id)).all())
    if not all_ids:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="No questions available"
        )
    k = min(settings.exam_question_count, len(all_ids))
    chosen_ids = random.sample(all_ids, k)

    questions = db.scalars(
        select(Question)
        .where(Question.id.in_(chosen_ids))
        .options(selectinload(Question.options))
    ).all()
    by_id = {q.id: q for q in questions}
    ordered = [by_id[qid] for qid in chosen_ids]

    attempt = Attempt(user_id=current_user.id, status="in_progress")
    attempt.answers = [
        AttemptAnswer(question_id=q.id, selected_option_ids=[], is_correct=False)
        for q in ordered
    ]
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return StartExamResponse(
        attempt_id=attempt.id,
        question_count=len(ordered),
        questions=[ExamQuestionOut.model_validate(q) for q in ordered],
    )
```

- [ ] **Step 4: Wire the exam router into `app/main.py`**

Update the routers import to include `exam`:

```python
from app.routers import auth, exam, health
```

And add this line after the auth router include:

```python
app.include_router(exam.router)
```

- [ ] **Step 5: Add `seed_questions` to `tests/helpers.py`**

Append to `backend/tests/helpers.py`:

```python
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
```

- [ ] **Step 6: Write the failing tests — `tests/test_exam_start.py`**

```python
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
```

- [ ] **Step 7: Run the tests (postgres + redis up)**

Run: `pytest tests/test_exam_start.py -v`
Expected: 5 tests PASS.

- [ ] **Step 8: Run the full suite**

Run: `pytest -q`
Expected: all pass (no regressions).

- [ ] **Step 9: Commit**

```bash
git add backend/app/models.py backend/app/exam_schemas.py backend/app/routers/exam.py backend/app/main.py backend/tests/helpers.py backend/tests/test_exam_start.py
git commit -m "feat(backend): add exam start endpoint with answer-key-safe questions"
```

---

### Task 3: Submit and server-side scoring endpoint

**Files:**
- Modify: `backend/app/routers/exam.py`
- Create: `backend/tests/test_exam_submit.py`

**Interfaces:**
- Consumes: `is_answer_correct` (Task 1), `SubmitExamRequest`/`ExamResultOut` (Task 2), `settings.pass_threshold`, the `AttemptAnswer.question` relationship (Task 2).
- Produces: `POST /exam/{attempt_id}/submit` → `ExamResultOut`. Scores every question in the attempt (unsubmitted = empty selection = wrong), sets `score`/`passed`/`status="completed"`/`finished_at`.

- [ ] **Step 1: Add imports to `app/routers/exam.py`**

Add to the top of the file (merge with existing imports):

```python
from datetime import datetime, timezone

from app.exam_schemas import ExamResultOut, SubmitExamRequest
from app.scoring import is_answer_correct
```

- [ ] **Step 2: Append the submit endpoint to `app/routers/exam.py`**

```python
@router.post("/{attempt_id}/submit", response_model=ExamResultOut)
def submit_exam(
    attempt_id: int,
    payload: SubmitExamRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ExamResultOut:
    attempt = db.scalar(
        select(Attempt)
        .where(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
        .options(
            selectinload(Attempt.answers)
            .selectinload(AttemptAnswer.question)
            .selectinload(Question.options)
        )
    )
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found"
        )
    if attempt.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Attempt already submitted"
        )

    submitted = {answer.question_id: answer for answer in payload.answers}
    score = 0
    for attempt_answer in attempt.answers:
        submission = submitted.get(attempt_answer.question_id)
        selected = set(submission.selected_option_ids) if submission else set()
        correct_ids = {
            option.id for option in attempt_answer.question.options if option.is_correct
        }
        attempt_answer.selected_option_ids = sorted(selected)
        attempt_answer.is_correct = is_answer_correct(correct_ids, selected)
        attempt_answer.time_taken = submission.time_taken if submission else None
        if attempt_answer.is_correct:
            score += 1

    total = len(attempt.answers)
    attempt.score = score
    attempt.passed = score >= settings.pass_threshold
    attempt.status = "completed"
    attempt.finished_at = datetime.now(timezone.utc)
    db.commit()

    return ExamResultOut(
        attempt_id=attempt.id, score=score, total=total, passed=attempt.passed
    )
```

- [ ] **Step 3: Write the failing tests — `tests/test_exam_submit.py`**

```python
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
    answers = _correct_answers(questions[: settings.pass_threshold]) + _wrong_answers(
        questions[settings.pass_threshold :]
    )
    body = client.post(f"/exam/{attempt_id}/submit", json={"answers": answers}).json()
    assert body["score"] == settings.pass_threshold
    assert body["passed"] is True


def test_one_below_threshold_fails(client, session):
    questions = seed_questions(session, 40)
    _register_and_login(client)
    attempt_id = client.post("/exam/start").json()["attempt_id"]
    n = settings.pass_threshold - 1
    answers = _correct_answers(questions[:n]) + _wrong_answers(questions[n:])
    body = client.post(f"/exam/{attempt_id}/submit", json={"answers": answers}).json()
    assert body["score"] == n
    assert body["passed"] is False


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
```

- [ ] **Step 4: Run the tests (postgres + redis up)**

Run: `pytest tests/test_exam_submit.py -v`
Expected: 7 tests PASS.

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/exam.py backend/tests/test_exam_submit.py
git commit -m "feat(backend): add exam submit endpoint with server-side scoring"
```

---

### Task 4: Review and history endpoints

**Files:**
- Modify: `backend/app/routers/exam.py`
- Create: `backend/tests/test_exam_review.py`
- Create: `backend/tests/test_exam_history.py`

**Interfaces:**
- Consumes: `ReviewOut`/`ReviewQuestionOut`/`ReviewOptionOut`/`AttemptSummaryOut` (Task 2), the `AttemptAnswer.question` relationship.
- Produces: `GET /exam/{attempt_id}/review` → `ReviewOut` (completed attempts only); `GET /exam/history` → `list[AttemptSummaryOut]`.

- [ ] **Step 1: Add imports to `app/routers/exam.py`**

Merge into the existing imports:

```python
from app.exam_schemas import (
    AttemptSummaryOut,
    ReviewOptionOut,
    ReviewOut,
    ReviewQuestionOut,
)
```

- [ ] **Step 2: Append the history endpoint to `app/routers/exam.py`**

Declare `history` before the `review` endpoint so the literal `/history` path is unambiguous:

```python
@router.get("/history", response_model=list[AttemptSummaryOut])
def exam_history(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[Attempt]:
    attempts = db.scalars(
        select(Attempt)
        .where(Attempt.user_id == current_user.id)
        .order_by(Attempt.started_at.desc())
    ).all()
    return list(attempts)
```

- [ ] **Step 3: Append the review endpoint to `app/routers/exam.py`**

```python
@router.get("/{attempt_id}/review", response_model=ReviewOut)
def review_exam(
    attempt_id: int,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> ReviewOut:
    attempt = db.scalar(
        select(Attempt)
        .where(Attempt.id == attempt_id, Attempt.user_id == current_user.id)
        .options(
            selectinload(Attempt.answers)
            .selectinload(AttemptAnswer.question)
            .selectinload(Question.options)
        )
    )
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found"
        )
    if attempt.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Attempt not completed"
        )

    questions = []
    for attempt_answer in attempt.answers:
        question = attempt_answer.question
        questions.append(
            ReviewQuestionOut(
                id=question.id,
                theme=question.theme,
                text=question.text,
                media_path=question.media_path,
                media_type=question.media_type,
                explanation=question.explanation,
                options=[ReviewOptionOut.model_validate(o) for o in question.options],
                selected_option_ids=list(attempt_answer.selected_option_ids),
                is_correct=attempt_answer.is_correct,
            )
        )

    return ReviewOut(
        attempt_id=attempt.id,
        score=attempt.score,
        total=len(attempt.answers),
        passed=attempt.passed,
        questions=questions,
    )
```

- [ ] **Step 4: Write the failing tests — `tests/test_exam_review.py`**

```python
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
```

- [ ] **Step 5: Write the failing tests — `tests/test_exam_history.py`**

```python
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
```

- [ ] **Step 6: Run the tests (postgres + redis up)**

Run: `pytest tests/test_exam_review.py tests/test_exam_history.py -v`
Expected: 4 + 3 = 7 tests PASS.

- [ ] **Step 7: Run the full suite**

Run: `pytest -q`
Expected: all pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/exam.py backend/tests/test_exam_review.py backend/tests/test_exam_history.py
git commit -m "feat(backend): add exam review and history endpoints"
```

---

## Self-Review

**Spec coverage (spec §6 Exam + Review + History):**
- Start creates an attempt, selects up to 40 random questions, returns them WITHOUT correct flags/explanations → Task 2. ✓
- Submit scores server-side with the all-or-nothing rule, sets `passed = score ≥ threshold`, marks completed → Task 3 + Task 1 scoring. ✓
- Review returns each question with the user's selection, correct answers, explanation, media → Task 4. ✓
- History lists past attempts (date, score, pass/fail) → Task 4. ✓
- Scoring isolated as a pure, exhaustively-tested function → Task 1. ✓
- Error codes 401/404/409 (spec §8) + ownership → Tasks 2–4. ✓

**Placeholder scan:** No TBDs; all code and test bodies concrete.

**Type consistency:** `is_answer_correct(set[int], set[int]) -> bool` used in Tasks 1, 3. Schema names (`StartExamResponse`, `SubmitExamRequest`, `ExamResultOut`, `ReviewOut`, `AttemptSummaryOut`) defined in Task 2, used in Tasks 3–4. `AttemptAnswer.question` relationship added in Task 2, consumed in Tasks 3–4. `settings.exam_question_count`/`pass_threshold` defined Task 1, used Tasks 2–3. `seed_questions(session, n, correct_label)` defined Task 2, used Tasks 2–4.

**Constraints honored:** all endpoints `Depends(get_current_user)` + `Depends(get_session)`; mutations are POST; ownership → 404; start leaks no answer keys (schema-enforced + test-asserted).

**Deferred (conscious):** Redis question-pool cache (YAGNI at current scale); per-theme results breakdown (spec §11 nice-to-have, deferred to frontend phase).

**Deferred to later phases:** Next.js frontend + exam UI/timer (Phase 4), polish + real content (Phase 5).
