import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_session
from app.deps import get_current_user
from app.exam_schemas import (
    AttemptSummaryOut,
    ExamQuestionOut,
    ExamResultOut,
    ReviewOptionOut,
    ReviewOut,
    ReviewQuestionOut,
    StartExamResponse,
    SubmitExamRequest,
)
from app.models import Attempt, AttemptAnswer, Question, User
from app.scoring import is_answer_correct

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


@router.get("/history", response_model=list[AttemptSummaryOut])
def exam_history(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[Attempt]:
    attempts = db.scalars(
        select(Attempt)
        .where(Attempt.user_id == current_user.id)
        .order_by(Attempt.started_at.desc(), Attempt.id.desc())
    ).all()
    return list(attempts)


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
