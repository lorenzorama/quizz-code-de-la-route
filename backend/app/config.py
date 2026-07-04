from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://quizz:quizz@localhost:5432/quizz"
    test_database_url: str = "postgresql+psycopg://quizz:quizz@localhost:5432/quizz_test"
    redis_url: str = "redis://localhost:6379/0"
    media_dir: str = "media"
    session_ttl_seconds: int = 60 * 60 * 24 * 7  # 7 days
    session_cookie_name: str = "session"
    cookie_secure: bool = False
    exam_question_count: int = 40
    pass_threshold: int = 35


settings = Settings()
