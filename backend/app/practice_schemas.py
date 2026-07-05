from pydantic import BaseModel, ConfigDict


class ThemeCount(BaseModel):
    theme: str
    count: int


class PracticeOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    label: str
    text: str
    is_correct: bool


class PracticeQuestion(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    theme: str
    text: str
    media_path: str | None
    media_type: str
    explanation: str
    options: list[PracticeOption]
