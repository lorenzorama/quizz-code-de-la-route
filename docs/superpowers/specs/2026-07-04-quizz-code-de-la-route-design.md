# Quizz Code de la Route — Design

**Date:** 2026-07-04
**Status:** Approved (design), pending implementation plan

## 1. Purpose

A web app to practice the French driving-license theory exam ("code de la route") as a
**faithful exam simulation**: 40 questions, timed, pass at 35/40. Beyond scoring, every
question carries an **explanation** so the learner understands *why* an answer is correct.
Questions and media (photos/videos) are authored in an Excel spreadsheet and imported into
the app. Small private user base (the author and a few people), with accounts so history
persists across devices.

## 2. Scope & non-goals

**In scope**
- Email + password accounts (small, private user base).
- Exam-simulation mode only: 40 random questions, 20s/question timer, no going back,
  score at the end, pass ≥ 35/40.
- Per-question mixed correct sets (single OR multiple correct answers; must select all
  correct and none incorrect to earn the point).
- Explanations + photo/video media per question.
- Attempt history per user, with a full review screen per attempt.
- Excel (`.xlsx`) question bank imported via a backend CLI. Placeholder content first;
  real questions + media populated later, collaboratively.
- Modern, lightweight, responsive UI/UX **from day one**.

**Non-goals (for now)**
- Practice-by-theme mode, free/immediate-feedback mode.
- Public sign-ups, email verification, password reset flows, OAuth/social login.
- Mobile-native apps.
- Cross-device media upload UI (media added via the folder + spreadsheet).

## 3. Tech stack

| Layer | Choice |
|---|---|
| Frontend | Next.js (App Router), React, TypeScript |
| Styling/UI | Tailwind CSS + a small custom component layer (Radix primitives where useful). Lightweight, no heavy component framework. |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| Cache/sessions | Redis |
| Containers | Docker + Docker Compose for the **backend stack** (`api` + `postgres` + `redis`) |
| xlsx parsing | `openpyxl` (backend import CLI) |
| Password hashing | argon2 |

**Runtime layout:** Docker Compose runs `api`, `postgres`, `redis`. The Next.js frontend
runs outside Docker for now (`npm run dev`), talking to the API over REST. Containerizing
the frontend can come later.

## 4. Architecture

```
┌─────────────────┐        REST / JSON       ┌──────────────────────────┐
│  Next.js (web)  │  ───────────────────▶    │  FastAPI backend         │
│  React + TS     │  ◀───────────────────    │  (Docker Compose)        │
│  Tailwind UI    │      httpOnly cookie     │   ├─ auth                │
└─────────────────┘                          │   ├─ exam + scoring      │
                                             │   ├─ /media static files │
                                             │   └─ xlsx import CLI     │
                                             └───────┬──────────┬───────┘
                                                     │          │
                                              ┌──────▼───┐  ┌───▼─────┐
                                              │ Postgres │  │  Redis  │
                                              └──────────┘  └─────────┘
```

- **Frontend** — pages: login/register, dashboard/history, exam runner, results & review.
  Auth via an httpOnly session cookie. No answer keys ever sent before scoring.
- **Backend** — owns auth, exam assembly, **server-side scoring**, history, and serving
  media files. Import CLI loads `questions.xlsx` → Postgres.
- **Postgres** — durable data.
- **Redis** — opaque session tokens → user; caches the assembled question pool; optional
  login rate-limit.

### Component boundaries (backend)

- `auth` — registration, login, logout, session validation. Depends on Postgres (users)
  and Redis (sessions).
- `questions/import` — parse `.xlsx`, validate rows, upsert questions + options. Depends
  on Postgres. Pure w.r.t. request lifecycle (runs as a CLI command).
- `exam` — start attempt (select 40 random questions, strip answer keys), submit answers,
  **scoring**, review, history. Depends on Postgres and Redis.
- `media` — static file mount serving the media folder at `/media/...`.

Scoring is isolated as a pure function `score(question, selected_option_ids) -> bool` so it
can be unit-tested exhaustively, independent of HTTP or DB.

## 5. Data model

| Table | Key fields |
|---|---|
| `users` | id, email (unique), password_hash, created_at |
| `questions` | id, ref (stable sheet key, e.g. `Q001`, unique), theme, text, media_path (nullable), media_type (`image`/`video`/`none`), explanation, created_at, updated_at |
| `options` | id, question_id (FK), label (`A`–`D`), text, is_correct (bool) |
| `attempts` | id, user_id (FK), started_at, finished_at (nullable), score (0–40, nullable until finished), passed (bool, nullable), status (`in_progress`/`completed`) |
| `attempt_answers` | id, attempt_id (FK), question_id (FK), selected_option_ids (json/array), is_correct (bool), time_taken (seconds, nullable) |

### Spreadsheet schema (`questions.xlsx`)

One row per question:

| Column | Meaning |
|---|---|
| `ref` | Stable unique key (`Q001`). Used for idempotent re-import. |
| `theme` | Category (e.g. `priorités`, `panneaux`, `vitesse`). |
| `question_text` | The prompt. |
| `option_a`..`option_d` | Answer texts (blank options allowed for <4 choices). |
| `correct` | Comma-separated correct labels, e.g. `A` or `A,C`. |
| `explanation` | Why the correct answer(s) are correct. |
| `media_path` | Relative path into the media folder, e.g. `signs/q001.jpg`. Blank = none. |
| `media_type` | `image`, `video`, or blank. |

Import is **idempotent by `ref`**: re-running updates existing questions/options rather
than duplicating. Placeholder rows + a `placeholder.png`/`placeholder.mp4` seed the app so
it works end-to-end before real content exists.

## 6. Key flows

### Auth
- Register: validate email + password, hash with argon2, create user.
- Login: verify password, create a Redis session (random opaque token → user id, with TTL),
  set an httpOnly, SameSite cookie.
- Logout: delete the Redis session, clear cookie.
- Protected endpoints validate the cookie against Redis.

### Exam
1. **Start** — create an `attempt` (`status=in_progress`); select **40 random questions**
   (pool cached in Redis). Return questions **without** `is_correct` flags or explanations.
2. **Run** (frontend) — 20s-per-question timer, auto-advance on timeout, **no going back**.
   Record selected option ids + time per question.
3. **Submit** — send all answers. Backend scores each with the pure `score()` function
   (point only when the selected set exactly equals the correct set), writes
   `attempt_answers`, sets `score`, `passed = score ≥ 35`, `status=completed`,
   `finished_at`.
4. **Review** — a review endpoint returns every question with the user's selection, the
   correct answer(s), the explanation, and media.

### History
- List past attempts (date, score, pass/fail badge). Selecting one opens its review.

## 7. UI / UX

Lightweight but modern, **from day one**:

- Tailwind CSS with a small, consistent design-token set (color, spacing, radius, shadow).
  System/`Inter` font, generous whitespace, rounded cards, subtle shadows.
- Clean exam runner: large question + media, clear A–D option cards with obvious
  selected state, a prominent countdown ring/bar for the 20s timer, progress indicator
  (`Question 12 / 40`).
- Results screen: big score, pass/fail state, per-theme breakdown if feasible; review list
  with correct/incorrect markers and explanations in expandable cards.
- Fully responsive (usable on phone and desktop). Accessible: keyboard-selectable options,
  sufficient contrast, focus states. Light theme first; dark theme optional later.
- No heavy UI framework — keep the bundle small; Radix primitives only where they earn
  their place (dialogs, etc.).

## 8. Error handling

- `401` unauthenticated / invalid session.
- `404` attempt or question not found.
- `409` re-submitting an already-completed attempt.
- `422` validation errors (bad register/login payloads, malformed submit).
- Import errors: row-level validation with a clear report (bad `correct` labels, missing
  media file) — fail loudly, don't silently import garbage.
- Frontend: the 20s timer is client-authoritative; network hiccups on submit are retried
  with a clear error state rather than losing the attempt.

## 9. Testing strategy

- **Scoring** — exhaustive `pytest` unit tests of the all-or-nothing multi-select rule
  (single-correct, multi-correct, partial selection, over-selection, empty selection).
- **Auth** — register/login/logout, session validation, wrong password, duplicate email.
- **Import** — valid rows, idempotent re-import by `ref`, invalid `correct` labels, missing
  media, `<4` options.
- **Exam endpoints** — start (no answer keys leaked), submit + score, review, history,
  and the `409`/`404` paths — against a test Postgres.
- **Frontend** — component tests for the timer/runner (auto-advance, no-back) and the
  review rendering.

## 10. Build phases

Each phase is independently runnable:

1. **Backend skeleton** — FastAPI app, Docker Compose (`api`+`postgres`+`redis`), config,
   DB models + migrations, `/media` static mount, xlsx import CLI with placeholder sheet
   + placeholder media.
2. **Auth** — register/login/logout, argon2 hashing, Redis sessions, protected-route
   dependency.
3. **Exam API** — start / submit / score / review / history endpoints, scoring function,
   Redis question-pool cache.
4. **Frontend** — Next.js + Tailwind design system, auth pages, exam runner (timer,
   progress, media), results & review, history. Modern UI from the start.
5. **Polish & content** — tests, accessibility pass, then populate real questions + media
   together.

## 11. Open items to resolve during content population

- Final theme taxonomy for `theme` column.
- Whether to show a per-theme breakdown on the results screen (nice-to-have).
- Real media dimensions/format conventions (image sizes, video length/codec).
