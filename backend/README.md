# Backend — Quizz Code de la Route

FastAPI backend for the French driving-test quiz app.

## Prerequisites

- Docker (for Postgres and Redis, or to run the full stack)
- [uv](https://github.com/astral-sh/uv) (Python package/venv manager)
- Python 3.12

## Setup

Create the virtual environment and install dependencies:

```bash
cd backend
uv venv --python 3.12 .venv
. .venv/bin/activate
uv pip install -r requirements.txt
```

Copy `.env.example` to `.env` and adjust if needed:

```bash
cp .env.example .env
```

## Start services

Start Postgres and Redis via Docker Compose:

```bash
docker compose up -d postgres redis
```

## Apply migrations

With the venv active:

```bash
python -m alembic upgrade head
```

(Bare `alembic upgrade head` also works, since `alembic/env.py` puts the
backend directory on `sys.path`.)

## Import the question bank

```bash
python -m app.cli import data/questions.xlsx
```

This is idempotent: re-running reports how many questions were created vs.
updated.

## Run tests

```bash
pytest
```

Tests use a separate `quizz_test` database (created automatically by the
`initdb` script when the `postgres` container is first initialized) and run
each test inside a rolled-back transaction.

## Authentication

The API uses cookie-based session authentication:

- `POST /auth/register` — create an account; returns `201` with the new user.
- `POST /auth/login` — verify credentials; returns `200` with the user and sets an
  httpOnly session cookie (`SESSION_COOKIE_NAME`, default `session`).
- `POST /auth/logout` — invalidate the session; returns `204` (also `204` if there
  was no active session).
- `GET /auth/me` — return the currently authenticated user.

Passwords are hashed with argon2. Sessions are opaque tokens backed by Redis
(`SESSION_TTL_SECONDS` controls their lifetime, default 7 days) — no JWTs, so a
logout or expiry immediately invalidates server-side access.

## Production security notes

- Set `COOKIE_SECURE=true` in production so the session cookie is HTTPS-only.
- Session cookies are `httpOnly` + `SameSite=Lax`. CSRF risk is mitigated by
  `SameSite=Lax` provided all state-changing operations stay POST/PUT/DELETE
  (never GET). For this small private app, not adding a CSRF token is an
  accepted risk; revisit (double-submit token) if the app becomes public.
  Phase 3 mutating endpoints (exam start/submit) must keep using non-GET
  methods.

## Run the API

Locally (with the venv active and services running):

```bash
uvicorn app.main:app --reload
```

Or run everything via Docker Compose:

```bash
docker compose up api
```

The API will be available at `http://localhost:8000`.
