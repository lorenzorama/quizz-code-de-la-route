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
