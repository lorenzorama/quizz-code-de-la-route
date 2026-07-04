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
