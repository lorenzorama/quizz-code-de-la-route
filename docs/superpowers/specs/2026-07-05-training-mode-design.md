# Training Mode ("Mode entraînement") — Design

**Date:** 2026-07-05
**Status:** Approved (design), pending implementation plan

## 1. Purpose

Add a **training mode** alongside the existing timed exam simulation. In training,
the learner practices at their own pace on one or more **themes** they choose, and
after validating each answer they immediately see the correct answer(s) and the
explanation. Training is a learning aid, not an assessment.

**Key differences from exam mode:**
- **No timer** (untimed, self-paced).
- **Per-question immediate feedback**: after the user validates their choice, the
  correct answer(s) + explanation are revealed for that question.
- **Theme-filtered**: the user selects one or more themes; the session mixes
  questions from all selected themes.
- **Ephemeral**: nothing is saved — no attempt, no score, no history entry.

## 2. Scope & non-goals

**In scope**
- Two authenticated, read-only backend endpoints: list themes (with counts), and
  fetch practice questions (with answer keys + explanations) filtered by selected
  themes.
- A `/practice` frontend page with two phases: multi-theme selection → untimed
  runner with per-question "Vérifier" reveal.
- A "Mode entraînement" entry on the dashboard.

**Non-goals**
- No persistence of training sessions (no attempts, no score, no history).
- No end-of-session recap/score.
- No timer.
- No changes to exam mode, the `attempts` model, or the DB schema.

## 3. Why this shape

Because training is ephemeral and explicitly reveals answers, there is **no exam
integrity concern** — the backend can return questions *with* `is_correct` and
`explanation`, and the frontend handles selection, validation, and reveal locally.
This avoids any new `attempt`/scoring/persistence machinery. The all-or-nothing
"correct?" verdict reuses the existing rule (selected set exactly equals the
correct set), computed client-side from the data already returned.

## 4. Backend

New router `app/routers/practice.py`, mounted in `app/main.py`, all endpoints
require `get_current_user` and use `Depends(get_session)` (GET only — no CSRF
surface). No new DB tables.

- `GET /practice/themes` → `list[ThemeCount]` where `ThemeCount = {theme: str, count: int}`.
  Distinct `questions.theme` values with the number of questions each, ordered by
  `theme`. Empty list if the bank is empty.
- `GET /practice/questions?theme=A&theme=B` → `list[PracticeQuestion]`.
  Repeated `theme` query params collect into a list. Returns the questions whose
  `theme` is in the provided set, **shuffled server-side**, each with full options
  including `is_correct`, plus `explanation`. If no `theme` params are provided,
  returns an empty list (the frontend always sends ≥1).

Schemas (`app/practice_schemas.py`):
- `ThemeCount {theme: str, count: int}`
- `PracticeOption {id: int, label: str, text: str, is_correct: bool}`
- `PracticeQuestion {id: int, theme: str, text: str, media_path: str | None, media_type: str, explanation: str, options: list[PracticeOption]}`

`PracticeQuestion` mirrors the review-time shape (answer key visible) minus the
per-attempt fields (`selected_option_ids`, question-level `is_correct`), which are
a client concern in training.

## 5. Frontend

### API client additions (`lib/api.ts`)
- Types `ThemeCount`, `PracticeOption`, `PracticeQuestion`.
- `getPracticeThemes(): Promise<ThemeCount[]>` → `GET /practice/themes`.
- `getPracticeQuestions(themes: string[]): Promise<PracticeQuestion[]>` → builds
  `/practice/questions?theme=…&theme=…` from the array (URL-encoded) and GETs it.

### Dashboard
A third card, **"Mode entraînement"**, next to "Examen blanc" and "Historique",
linking to `/practice`.

### `/practice` page (one route, two phases via component state)
Wrapped in `RequireAuth` + `TopBar`.

**Phase 1 — theme selection.** Fetch `getPracticeThemes()`. Render one toggle card
per theme showing its name + question count; multi-select (a `Set<string>` of
chosen themes). A "Tout sélectionner / tout désélectionner" convenience toggle. A
**"Commencer"** button, disabled until ≥1 theme is selected. On click, fetch
`getPracticeQuestions([...selected])` and move to phase 2. Empty bank → an empty
state pointing back to the dashboard.

**Phase 2 — untimed runner.** No timer anywhere. For the current question:
1. Show theme badge, question text, media (`QuestionMedia`), and options as
   selectable `OptionCard`s (multi-select toggle) — same interaction as the exam.
2. A **"Vérifier"** button (disabled if nothing selected). On click, reveal the
   correction for this question: correct options in green, the user's incorrect
   picks in red, the **explanation**, and a **"Correct ✅ / Incorrect ❌"** verdict
   (all-or-nothing: selected set === correct set). The reveal reuses the existing
   `ReviewQuestionCard` presentation by constructing a review-shaped object from
   the practice question + the user's selection + the computed `is_correct`.
3. After revealing, a **"Suivant"** button advances to the next question (fresh,
   unrevealed); on the last question the button is **"Terminer"** and returns to
   phase 1 (theme selection reset).

If the selected themes yield no questions, the runner shows an empty state and a
way back to selection.

### Reuse
`OptionCard` (selection), `QuestionMedia` (media, already viewport-friendly),
`ReviewQuestionCard` (reveal), `Button`/`Card` (design system). New: the
`/practice` page, its two-phase logic, and the theme-selection UI.

## 6. Error handling
- `401` on unauthenticated access to `/practice/*` (frontend `RequireAuth` also
  guards the page).
- No themes / empty bank → empty states in the UI, not errors.
- Selected themes with no questions → runner empty state.
- Network failure fetching themes/questions → a clear error message with a retry
  or a link back to the dashboard.

## 7. Testing
- **Backend:** `/practice/themes` grouping + counts; `/practice/questions` theme
  filtering (single and multiple themes), that options expose `is_correct` and the
  question exposes `explanation`, unknown/empty theme set → empty list, and `401`
  when unauthenticated.
- **Frontend:** api client builds the repeated-`theme` query correctly; the theme
  selector renders themes and enables "Commencer" only when ≥1 is selected; the
  runner reveals the explanation + correct/incorrect on "Vérifier" and advances on
  "Suivant"; and there is **no countdown/timer** element in the training runner.

## 8. Deferred (unchanged from before)
Real question/media content population; per-theme results breakdown for exams;
single-active-attempt policy; other Phase 5 polish.
