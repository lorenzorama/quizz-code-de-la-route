import random

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.db import get_session
from app.deps import get_current_user
from app.models import Question, User
from app.practice_schemas import PracticeQuestion, ThemeCount

router = APIRouter(prefix="/practice", tags=["practice"])


@router.get("/themes", response_model=list[ThemeCount])
def list_themes(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[ThemeCount]:
    rows = db.execute(
        select(Question.theme, func.count(Question.id))
        .group_by(Question.theme)
        .order_by(Question.theme)
    ).all()
    return [ThemeCount(theme=theme, count=count) for theme, count in rows]


@router.get("/questions", response_model=list[PracticeQuestion])
def practice_questions(
    theme: list[str] = Query(default=[]),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
) -> list[Question]:
    if not theme:
        return []
    questions = list(
        db.scalars(
            select(Question)
            .where(Question.theme.in_(theme))
            .options(selectinload(Question.options))
        ).all()
    )
    random.shuffle(questions)
    return questions
