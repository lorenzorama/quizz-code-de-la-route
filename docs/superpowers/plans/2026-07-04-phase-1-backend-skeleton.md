# Phase 1 — Backend Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the FastAPI backend skeleton with Postgres + Redis via Docker Compose, the full database model, a `/media` static mount with a placeholder image, and an idempotent `.xlsx` question-import CLI — all test-covered.

**Architecture:** A FastAPI app (`backend/app`) with settings via `pydantic-settings`, SQLAlchemy 2.0 ORM models, Alembic migrations, a Redis client, and an import module split into a pure `parse_workbook()` (validation, no DB) and a DB-facing `import_questions()` (idempotent upsert by `ref`). Postgres and Redis run in Docker Compose; the API can also run in Compose. Tests run with `pytest` against a `quizz_test` Postgres database created by a Compose init script.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.0, Alembic, psycopg 3, redis-py, pydantic-settings, openpyxl, pytest, httpx (TestClient), Docker + Docker Compose (Postgres 16, Redis 7).

## Global Constraints

- Python version: **3.12** (Docker base `python:3.12-slim`). Locally, Python 3.12 is provided via **`uv`** (already installed); create the venv with `uv venv --python 3.12 .venv` and install deps with `uv pip install`.
- Postgres image: **postgres:16**. Redis image: **redis:7**.
- All backend code lives under `backend/`. Package root is `backend/app/`.
- SQLAlchemy **2.0 style** only (`DeclarativeBase`, `Mapped`, `mapped_column`).
- DB access URLs use the **`postgresql+psycopg://`** driver prefix (psycopg 3).
- Import is **idempotent by `questions.ref`**: re-running updates, never duplicates.
- Table/column names exactly as in the spec data model (`users`, `questions`, `options`, `attempts`, `attempt_answers`).
- Every task ends with a passing test run and a commit.
- Run all commands from the `backend/` directory unless stated otherwise.

---

### Task 1: Backend scaffold, config, and health endpoint

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/.gitignore`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/health.py`
- Create: `backend/app/main.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_health.py`
- Create: `backend/pytest.ini`

**Interfaces:**
- Produces: `app.main:app` (FastAPI instance); `app.config.settings` with attributes `database_url`, `test_database_url`, `redis_url`, `media_dir` (all `str`); `GET /health` → `{"status": "ok"}`.

- [ ] **Step 1: Create `requirements.txt`**

```
fastapi==0.115.*
uvicorn[standard]==0.32.*
sqlalchemy==2.0.*
alembic==1.14.*
psycopg[binary]==3.2.*
redis==5.2.*
pydantic-settings==2.6.*
openpyxl==3.1.*
pytest==8.3.*
httpx==0.27.*
```

- [ ] **Step 2: Create `.env.example`**

```
DATABASE_URL=postgresql+psycopg://quizz:quizz@localhost:5432/quizz
TEST_DATABASE_URL=postgresql+psycopg://quizz:quizz@localhost:5432/quizz_test
REDIS_URL=redis://localhost:6379/0
MEDIA_DIR=media
```

- [ ] **Step 3: Create `.gitignore`** (backend-local)

```
__pycache__/
*.pyc
.env
.venv/
venv/
.pytest_cache/
```

- [ ] **Step 4: Create the package files**

`backend/app/__init__.py`: empty file.
`backend/app/routers/__init__.py`: empty file.
`backend/tests/__init__.py`: empty file.

- [ ] **Step 5: Create `app/config.py`**

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://quizz:quizz@localhost:5432/quizz"
    test_database_url: str = "postgresql+psycopg://quizz:quizz@localhost:5432/quizz_test"
    redis_url: str = "redis://localhost:6379/0"
    media_dir: str = "media"


settings = Settings()
```

- [ ] **Step 6: Create `app/routers/health.py`**

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 7: Create `app/main.py`**

```python
from fastapi import FastAPI

from app.routers import health

app = FastAPI(title="Quizz Code de la Route API")
app.include_router(health.router)


@app.get("/")
def root() -> dict:
    return {"service": "quizz-code-de-la-route", "status": "ok"}
```

- [ ] **Step 8: Create `pytest.ini`**

```ini
[pytest]
pythonpath = .
testpaths = tests
```

- [ ] **Step 9: Write the failing test — `tests/test_health.py`**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_root_returns_service_name():
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json()["service"] == "quizz-code-de-la-route"
```

- [ ] **Step 10: Set up venv and install (from `backend/`)**

Run:
```bash
cd backend && uv venv --python 3.12 .venv && . .venv/bin/activate && uv pip install -r requirements.txt
```
Expected: creates a Python 3.12 venv and installs complete without error. (All later `pytest`/`alembic`/`python`/`uvicorn` commands run inside this activated venv.)

- [ ] **Step 11: Run the test**

Run: `pytest tests/test_health.py -v`
Expected: 2 tests PASS.

- [ ] **Step 12: Commit**

```bash
git add backend/
git commit -m "feat(backend): scaffold FastAPI app with config and health endpoint"
```

---

### Task 2: Docker Compose stack (api + postgres + redis)

**Files:**
- Create: `backend/Dockerfile`
- Create: `backend/.dockerignore`
- Create: `backend/docker-compose.yml`
- Create: `backend/initdb/01-create-test-db.sql`

**Interfaces:**
- Consumes: `app.main:app` from Task 1.
- Produces: `docker compose up` serving the API on `localhost:8000`; a `postgres` service (db `quizz`, user/pass `quizz`) with a `quizz_test` database auto-created; a `redis` service on `localhost:6379`.

- [ ] **Step 1: Create `Dockerfile`**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Create `.dockerignore`**

```
.venv/
venv/
__pycache__/
.pytest_cache/
.env
*.pyc
```

- [ ] **Step 3: Create `initdb/01-create-test-db.sql`**

```sql
CREATE DATABASE quizz_test;
```

- [ ] **Step 4: Create `docker-compose.yml`**

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+psycopg://quizz:quizz@postgres:5432/quizz
      REDIS_URL: redis://redis:6379/0
      MEDIA_DIR: media
    depends_on:
      - postgres
      - redis
    volumes:
      - ./media:/app/media

  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: quizz
      POSTGRES_PASSWORD: quizz
      POSTGRES_DB: quizz
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./initdb:/docker-entrypoint-initdb.d

  redis:
    image: redis:7
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

- [ ] **Step 5: Validate the Compose file**

Run: `docker compose config`
Expected: prints the resolved config with no error (services `api`, `postgres`, `redis`).

- [ ] **Step 6: Bring up postgres + redis and verify**

Run:
```bash
docker compose up -d postgres redis
docker compose exec postgres psql -U quizz -d quizz_test -c "SELECT 1;"
docker compose exec redis redis-cli ping
```
Expected: `psql` prints a row with `1`; `redis-cli` prints `PONG`. (If the volume already existed from a prior run without the init script, run `docker compose down -v` first so the init script re-runs.)

- [ ] **Step 7: Commit**

```bash
git add backend/Dockerfile backend/.dockerignore backend/docker-compose.yml backend/initdb/
git commit -m "feat(backend): add docker compose stack with postgres and redis"
```

---

### Task 3: Database layer — models, session, Alembic migration

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/models.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_models.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/` (directory, keep with a `.gitkeep`)

**Interfaces:**
- Consumes: `app.config.settings` from Task 1.
- Produces:
  - `app.db.Base` (DeclarativeBase), `app.db.engine`, `app.db.SessionLocal`, `app.db.get_session` (FastAPI dependency generator yielding a `Session`).
  - `app.models` classes: `User(id, email, password_hash, created_at)`,
    `Question(id, ref, theme, text, media_path, media_type, explanation, created_at, updated_at, options)`,
    `Option(id, question_id, label, text, is_correct, question)`,
    `Attempt(id, user_id, started_at, finished_at, score, passed, status, answers)`,
    `AttemptAnswer(id, attempt_id, question_id, selected_option_ids, is_correct, time_taken, attempt)`.
  - Test fixtures `engine` (session-scoped) and `session` (function-scoped, transaction-rolled-back) in `conftest.py`.

- [ ] **Step 1: Create `app/db.py`**

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Create `app/models.py`**

```python
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(primary_key=True)
    ref: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    theme: Mapped[str] = mapped_column(String(100), default="")
    text: Mapped[str] = mapped_column(Text)
    media_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_type: Mapped[str] = mapped_column(String(10), default="none")
    explanation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    options: Mapped[list["Option"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="Option.label",
    )


class Option(Base):
    __tablename__ = "options"

    id: Mapped[int] = mapped_column(primary_key=True)
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(1))
    text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    question: Mapped["Question"] = relationship(back_populates="options")


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    passed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")

    answers: Mapped[list["AttemptAnswer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


class AttemptAnswer(Base):
    __tablename__ = "attempt_answers"

    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE")
    )
    selected_option_ids: Mapped[list] = mapped_column(JSON, default=list)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    time_taken: Mapped[int | None] = mapped_column(Integer, nullable=True)

    attempt: Mapped["Attempt"] = relationship(back_populates="answers")
```

- [ ] **Step 3: Create `tests/conftest.py`**

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  (register mappers on Base.metadata)
from app.config import settings
from app.db import Base


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(settings.test_database_url)
    Base.metadata.drop_all(eng)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def session(engine) -> Session:
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection, expire_on_commit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()
```

- [ ] **Step 4: Write the failing test — `tests/test_models.py`**

```python
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
    session.add(user)
    session.flush()
    attempt = Attempt(user_id=user.id, status="in_progress")
    attempt.answers = [
        AttemptAnswer(question_id=1, selected_option_ids=[10, 11], is_correct=True)
    ]
    session.add(attempt)
    session.flush()
    assert attempt.answers[0].selected_option_ids == [10, 11]
    assert attempt.status == "in_progress"
```

- [ ] **Step 5: Run the test to verify it fails**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — collection/DB error because tables don't exist yet is NOT expected (conftest creates tables); it should actually PASS once models exist. If models had an error it FAILs. Proceed to confirm PASS in Step 6. (Ensure `docker compose up -d postgres redis` is running so `quizz_test` is reachable.)

- [ ] **Step 6: Run the test to verify it passes**

Run: `pytest tests/test_models.py -v`
Expected: 3 tests PASS.

- [ ] **Step 7: Create `alembic.ini`**

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+psycopg://quizz:quizz@localhost:5432/quizz

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

- [ ] **Step 8: Create `alembic/script.py.mako`**

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 9: Create `alembic/env.py`**

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401  (register models)
from app.config import settings
from app.db import Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        {"sqlalchemy.url": settings.database_url},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [ ] **Step 10: Create the versions directory placeholder**

Create `backend/alembic/versions/.gitkeep` (empty file).

- [ ] **Step 11: Autogenerate the initial migration**

Run (with `docker compose up -d postgres redis` running):
```bash
alembic revision --autogenerate -m "initial schema"
```
Expected: a new file appears in `alembic/versions/` containing `op.create_table("users", ...)`, `"questions"`, `"options"`, `"attempts"`, `"attempt_answers"`. Open it and confirm all five tables are present.

- [ ] **Step 12: Apply the migration and verify**

Run:
```bash
alembic upgrade head
docker compose exec postgres psql -U quizz -d quizz -c "\dt"
```
Expected: `\dt` lists `users`, `questions`, `options`, `attempts`, `attempt_answers`, `alembic_version`.

- [ ] **Step 13: Commit**

```bash
git add backend/app/db.py backend/app/models.py backend/tests/conftest.py backend/tests/test_models.py backend/alembic.ini backend/alembic/
git commit -m "feat(backend): add ORM models, session layer, and initial migration"
```

---

### Task 4: Redis client and enriched health check

**Files:**
- Create: `backend/app/redis_client.py`
- Modify: `backend/app/routers/health.py`
- Create: `backend/tests/test_health_deps.py`

**Interfaces:**
- Consumes: `app.config.settings`, `app.db.engine`.
- Produces: `app.redis_client.get_redis()` → a `redis.Redis` client (decoded responses); `GET /health` now returns `{"status": "ok", "database": "ok"|"error", "redis": "ok"|"error"}` and responds `503` if either dependency is down.

- [ ] **Step 1: Create `app/redis_client.py`**

```python
import redis

from app.config import settings

_client: redis.Redis | None = None


def get_redis() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    return _client
```

- [ ] **Step 2: Rewrite `app/routers/health.py`**

```python
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.db import engine
from app.redis_client import get_redis

router = APIRouter()


@router.get("/health")
def health() -> JSONResponse:
    db_ok = True
    redis_ok = True

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    try:
        get_redis().ping()
    except Exception:
        redis_ok = False

    payload = {
        "status": "ok" if db_ok and redis_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "redis": "ok" if redis_ok else "error",
    }
    code = 200 if db_ok and redis_ok else 503
    return JSONResponse(payload, status_code=code)
```

- [ ] **Step 3: Update the existing health test expectation**

In `tests/test_health.py`, replace `test_health_returns_ok` with:

```python
def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body["redis"] == "ok"
```

- [ ] **Step 4: Write the failing test — `tests/test_health_deps.py`**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_dependency_status():
    resp = client.get("/health")
    body = resp.json()
    assert set(body.keys()) == {"status", "database", "redis"}
    assert body["database"] in {"ok", "error"}
    assert body["redis"] in {"ok", "error"}
```

- [ ] **Step 5: Run the tests (requires postgres + redis up)**

Run: `pytest tests/test_health.py tests/test_health_deps.py -v`
Expected: all PASS (database and redis report `ok` with Compose services running).

- [ ] **Step 6: Commit**

```bash
git add backend/app/redis_client.py backend/app/routers/health.py backend/tests/test_health.py backend/tests/test_health_deps.py
git commit -m "feat(backend): add redis client and dependency-aware health check"
```

---

### Task 5: Media static mount with placeholder image

**Files:**
- Modify: `backend/app/main.py`
- Create: `backend/media/placeholder.png` (generated)
- Create: `backend/media/.gitkeep`
- Create: `backend/tests/test_media.py`

**Interfaces:**
- Consumes: `app.config.settings.media_dir`, `app.main:app`.
- Produces: static mount so `GET /media/<path>` serves files from the media directory; `GET /media/placeholder.png` → `200` with content-type `image/png`.

- [ ] **Step 1: Generate the placeholder PNG**

Run (from `backend/`):
```bash
mkdir -p media
python -c "import base64,pathlib; pathlib.Path('media/placeholder.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='))"
touch media/.gitkeep
```
Expected: `media/placeholder.png` exists (a 1×1 PNG placeholder).

- [ ] **Step 2: Modify `app/main.py` to mount media**

```python
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers import health

app = FastAPI(title="Quizz Code de la Route API")
app.include_router(health.router)

os.makedirs(settings.media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")


@app.get("/")
def root() -> dict:
    return {"service": "quizz-code-de-la-route", "status": "ok"}
```

- [ ] **Step 3: Write the failing test — `tests/test_media.py`**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_placeholder_media_is_served():
    resp = client.get("/media/placeholder.png")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"


def test_missing_media_returns_404():
    resp = client.get("/media/does-not-exist.png")
    assert resp.status_code == 404
```

- [ ] **Step 4: Run the test**

Run: `pytest tests/test_media.py -v`
Expected: 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/main.py backend/media/ backend/tests/test_media.py
git commit -m "feat(backend): serve media directory with placeholder image"
```

---

### Task 6: xlsx parser — pure validation (`parse_workbook`)

**Files:**
- Create: `backend/app/importer.py`
- Create: `backend/tests/test_parse_workbook.py`
- Create: `backend/tests/helpers.py`

**Interfaces:**
- Produces:
  - `class QuestionImportError(Exception)`.
  - `@dataclass OptionRow(label: str, text: str, is_correct: bool)`.
  - `@dataclass QuestionRow(ref: str, theme: str, text: str, options: list[OptionRow], explanation: str, media_path: str | None, media_type: str)`.
  - `parse_workbook(path: str) -> list[QuestionRow]` — reads the first worksheet, validates, raises `QuestionImportError` on bad data.
  - Required columns: `ref, theme, question_text, option_a, option_b, option_c, option_d, correct, explanation, media_path, media_type`.

- [ ] **Step 1: Create `app/importer.py` (parser portion)**

```python
from dataclasses import dataclass

import openpyxl

VALID_LABELS = ["A", "B", "C", "D"]
VALID_MEDIA_TYPES = {"image", "video", "none"}
REQUIRED_COLUMNS = [
    "ref",
    "theme",
    "question_text",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct",
    "explanation",
    "media_path",
    "media_type",
]


class QuestionImportError(Exception):
    pass


@dataclass
class OptionRow:
    label: str
    text: str
    is_correct: bool


@dataclass
class QuestionRow:
    ref: str
    theme: str
    text: str
    options: list[OptionRow]
    explanation: str
    media_path: str | None
    media_type: str


def parse_workbook(path: str) -> list[QuestionRow]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise QuestionImportError("Workbook is empty")

    header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise QuestionImportError(f"Missing columns: {missing}")
    idx = {name: header.index(name) for name in REQUIRED_COLUMNS}

    def cell(raw: tuple, name: str) -> str:
        value = raw[idx[name]]
        return "" if value is None else str(value).strip()

    result: list[QuestionRow] = []
    seen: set[str] = set()

    for line_no, raw in enumerate(rows[1:], start=2):
        ref = cell(raw, "ref")
        if not ref:
            continue  # skip blank rows

        if ref in seen:
            raise QuestionImportError(f"Row {line_no}: duplicate ref {ref!r}")
        seen.add(ref)

        correct = [c.strip().upper() for c in cell(raw, "correct").split(",") if c.strip()]
        if not correct:
            raise QuestionImportError(f"Row {line_no} ({ref}): no correct answer given")
        bad = [c for c in correct if c not in VALID_LABELS]
        if bad:
            raise QuestionImportError(f"Row {line_no} ({ref}): invalid correct labels {bad}")

        options: list[OptionRow] = []
        for label in VALID_LABELS:
            text = cell(raw, f"option_{label.lower()}")
            if text:
                options.append(OptionRow(label=label, text=text, is_correct=label in correct))
        if len(options) < 2:
            raise QuestionImportError(f"Row {line_no} ({ref}): needs at least 2 options")

        option_labels = {o.label for o in options}
        orphan = [c for c in correct if c not in option_labels]
        if orphan:
            raise QuestionImportError(
                f"Row {line_no} ({ref}): correct label(s) {orphan} have no option text"
            )

        media_type = cell(raw, "media_type").lower() or "none"
        if media_type not in VALID_MEDIA_TYPES:
            raise QuestionImportError(
                f"Row {line_no} ({ref}): invalid media_type {media_type!r}"
            )
        media_path = cell(raw, "media_path") or None

        result.append(
            QuestionRow(
                ref=ref,
                theme=cell(raw, "theme"),
                text=cell(raw, "question_text"),
                options=options,
                explanation=cell(raw, "explanation"),
                media_path=media_path,
                media_type=media_type,
            )
        )

    return result
```

- [ ] **Step 2: Create `tests/helpers.py` (build an xlsx in a temp dir)**

```python
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
```

- [ ] **Step 3: Write the failing tests — `tests/test_parse_workbook.py`**

```python
import pytest

from app.importer import QuestionImportError, parse_workbook
from tests.helpers import valid_row, write_workbook


def test_parses_single_correct(tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(correct="B")])
    rows = parse_workbook(path)
    assert len(rows) == 1
    q = rows[0]
    assert q.ref == "Q001"
    assert q.media_type == "image"
    assert [o.label for o in q.options if o.is_correct] == ["B"]


def test_parses_multi_correct(tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(correct="A,C")])
    rows = parse_workbook(path)
    correct = {o.label for o in rows[0].options if o.is_correct}
    assert correct == {"A", "C"}


def test_blank_rows_skipped(tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(), {"ref": ""}])
    assert len(parse_workbook(path)) == 1


def test_missing_media_becomes_none(tmp_path):
    path = write_workbook(
        tmp_path / "q.xlsx", [valid_row(media_path="", media_type="none")]
    )
    assert parse_workbook(path)[0].media_path is None


def test_invalid_correct_label_raises(tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(correct="Z")])
    with pytest.raises(QuestionImportError, match="invalid correct labels"):
        parse_workbook(path)


def test_no_correct_answer_raises(tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(correct="")])
    with pytest.raises(QuestionImportError, match="no correct answer"):
        parse_workbook(path)


def test_correct_label_without_option_text_raises(tmp_path):
    path = write_workbook(
        tmp_path / "q.xlsx", [valid_row(correct="D", option_d="")]
    )
    with pytest.raises(QuestionImportError, match="no option text"):
        parse_workbook(path)


def test_duplicate_ref_raises(tmp_path):
    path = write_workbook(
        tmp_path / "q.xlsx", [valid_row(ref="Q001"), valid_row(ref="Q001")]
    )
    with pytest.raises(QuestionImportError, match="duplicate ref"):
        parse_workbook(path)


def test_invalid_media_type_raises(tmp_path):
    path = write_workbook(tmp_path / "q.xlsx", [valid_row(media_type="gif")])
    with pytest.raises(QuestionImportError, match="invalid media_type"):
        parse_workbook(path)


def test_too_few_options_raises(tmp_path):
    path = write_workbook(
        tmp_path / "q.xlsx",
        [valid_row(option_b="", option_c="", option_d="", correct="A")],
    )
    with pytest.raises(QuestionImportError, match="at least 2 options"):
        parse_workbook(path)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/test_parse_workbook.py -v`
Expected: 10 tests PASS. (No DB needed — parser is pure.)

- [ ] **Step 5: Commit**

```bash
git add backend/app/importer.py backend/tests/test_parse_workbook.py backend/tests/helpers.py
git commit -m "feat(backend): add xlsx question parser with validation"
```

---

### Task 7: Import upsert, CLI, and placeholder spreadsheet

**Files:**
- Modify: `backend/app/importer.py`
- Create: `backend/app/cli.py`
- Create: `backend/scripts/make_placeholder_xlsx.py`
- Create: `backend/data/questions.xlsx` (generated)
- Create: `backend/tests/test_import_questions.py`

**Interfaces:**
- Consumes: `parse_workbook`, `QuestionRow` (Task 6); `app.models.Question`, `app.models.Option` (Task 3); `app.db.SessionLocal` (Task 3).
- Produces:
  - `import_questions(session: Session, rows: list[QuestionRow]) -> dict` returning `{"created": int, "updated": int}`; idempotent upsert keyed on `Question.ref`; replaces a question's options on each import.
  - `python -m app.cli import <path.xlsx>` — parses then imports, printing a summary.
  - `backend/data/questions.xlsx` — placeholder bank (3 rows) usable end-to-end.

- [ ] **Step 1: Append `import_questions` to `app/importer.py`**

Add these imports at the top of `app/importer.py` (below the existing `import openpyxl`):

```python
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Option, Question
```

Then append at the end of the file:

```python
def import_questions(session: Session, rows: list[QuestionRow]) -> dict:
    created = 0
    updated = 0
    for row in rows:
        question = session.scalar(select(Question).where(Question.ref == row.ref))
        if question is None:
            question = Question(ref=row.ref)
            session.add(question)
            created += 1
        else:
            updated += 1

        question.theme = row.theme
        question.text = row.text
        question.explanation = row.explanation
        question.media_path = row.media_path
        question.media_type = row.media_type

        question.options.clear()
        session.flush()
        for option in row.options:
            question.options.append(
                Option(label=option.label, text=option.text, is_correct=option.is_correct)
            )

    session.commit()
    return {"created": created, "updated": updated}
```

- [ ] **Step 2: Create `app/cli.py`**

```python
import sys

from app.db import SessionLocal
from app.importer import import_questions, parse_workbook


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] != "import":
        print("Usage: python -m app.cli import <path-to-xlsx>")
        return 1

    rows = parse_workbook(argv[1])
    with SessionLocal() as session:
        stats = import_questions(session, rows)
    print(f"Imported: {stats['created']} created, {stats['updated']} updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Create `scripts/make_placeholder_xlsx.py`**

```python
import pathlib

import openpyxl

HEADERS = [
    "ref", "theme", "question_text",
    "option_a", "option_b", "option_c", "option_d",
    "correct", "explanation", "media_path", "media_type",
]

ROWS = [
    ["Q001", "priorités", "À cette intersection sans signalisation, qui passe en premier ? (PLACEHOLDER)",
     "Moi", "Le véhicule venant de droite", "Le véhicule venant de gauche", "Personne",
     "B", "PLACEHOLDER : sans signalisation, la priorité est au véhicule venant de la droite.",
     "placeholder.png", "image"],
    ["Q002", "panneaux", "Que signifie ce panneau ? (PLACEHOLDER)",
     "Danger", "Interdiction de tourner", "Obligation de tourner", "Fin d'interdiction",
     "A,B", "PLACEHOLDER : explication à compléter avec le vrai contenu.",
     "placeholder.png", "image"],
    ["Q003", "vitesse", "Quelle est la vitesse maximale autorisée ici ? (PLACEHOLDER)",
     "50 km/h", "80 km/h", "90 km/h", "130 km/h",
     "B", "PLACEHOLDER : explication à compléter.",
     "", "none"],
]


def main() -> None:
    out = pathlib.Path("data")
    out.mkdir(exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "questions"
    ws.append(HEADERS)
    for row in ROWS:
        ws.append(row)
    wb.save(out / "questions.xlsx")
    print(f"wrote {out / 'questions.xlsx'}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Generate the placeholder spreadsheet**

Run (from `backend/`): `python scripts/make_placeholder_xlsx.py`
Expected: prints `wrote data/questions.xlsx`; file exists.

- [ ] **Step 5: Write the failing tests — `tests/test_import_questions.py`**

```python
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
```

- [ ] **Step 6: Run the tests (requires postgres up)**

Run: `pytest tests/test_import_questions.py -v`
Expected: 3 tests PASS.

- [ ] **Step 7: End-to-end CLI check against the real DB**

Run (with `docker compose up -d postgres redis` and `alembic upgrade head` already applied):
```bash
python -m app.cli import data/questions.xlsx
```
Expected: prints `Imported: 3 created, 0 updated`. Running it a second time prints `Imported: 0 created, 3 updated`.

- [ ] **Step 8: Run the whole suite**

Run: `pytest -v`
Expected: all tests across all files PASS.

- [ ] **Step 9: Commit**

```bash
git add backend/app/importer.py backend/app/cli.py backend/scripts/ backend/data/ backend/tests/test_import_questions.py
git commit -m "feat(backend): add idempotent question import CLI and placeholder bank"
```

---

## Self-Review

**Spec coverage (Phase 1 items):**
- FastAPI app + Docker Compose (`api`+`postgres`+`redis`) → Tasks 1, 2. ✓
- Config → Task 1. ✓
- DB models + migrations → Task 3. ✓
- `/media` static mount + placeholder media → Task 5. ✓
- xlsx import CLI with placeholder sheet + placeholder media → Tasks 6, 7. ✓
- Redis wiring (used later for sessions/cache) → Task 4 establishes the client + health ping. ✓
- Data model tables/columns match spec §5 exactly. ✓
- Idempotent-by-`ref` import (spec §5) → Task 7. ✓
- Import validation fails loudly (spec §8) → Task 6. ✓

**Placeholder scan:** No "TBD"/"add error handling"-style gaps; all code shown in full; test bodies concrete.

**Type consistency:** `parse_workbook -> list[QuestionRow]`, `import_questions(session, rows) -> dict` used identically in Tasks 6, 7, and tests. `QuestionRow`/`OptionRow` field names consistent. `settings` attribute names (`database_url`, `test_database_url`, `redis_url`, `media_dir`) consistent across config, db, conftest, alembic, main. Model class/relationship names (`Question.options`, `Attempt.answers`) consistent between Task 3 and Task 7.

**Deferred to later phases:** auth (Phase 2), exam/scoring/review/history endpoints (Phase 3), Next.js frontend + UI (Phase 4), full test/accessibility polish + real content (Phase 5). Each gets its own plan.
