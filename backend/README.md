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
