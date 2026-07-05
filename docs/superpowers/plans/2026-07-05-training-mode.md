# Training Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an ephemeral, theme-filtered training mode with per-question immediate feedback (correct answers + explanations revealed after the user validates), no timer, no persistence.

**Architecture:** Two authenticated read-only backend endpoints expose themes (with counts) and practice questions **with** answer keys + explanations (no exam-integrity concern in training). A single `/practice` frontend page runs two phases in component state — multi-theme selection, then an untimed runner that reveals the correction (reusing `ReviewQuestionCard`) on "Vérifier". No `attempt`, no score, no DB change.

**Tech Stack:** Backend FastAPI + SQLAlchemy 2.0 (new `practice` router + schemas). Frontend Next.js App Router + Tailwind, Vitest. Reuses Phase 4 components.

## Global Constraints

- **Backend:** new endpoints live under a `practice` router, all `Depends(get_current_user)` + `Depends(get_session)`, **GET only**. No new DB tables/migration. Practice questions intentionally include `is_correct` + `explanation` (training reveals answers).
- **Frontend Node:** before any npm command run `export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"; cd frontend && nvm use` (`.nvmrc` → v20.20.2). node_modules already installed; do NOT reinstall.
- Keep `npm run lint` at **exit 0**, `npm test` all pass, `npm run build` clean — verify all three before each frontend commit. Backend: `pytest` all pass before its commit.
- **Ephemeral:** no attempt creation, no score, no history — training saves nothing.
- UI copy in **French**. Reuse `OptionCard`, `QuestionMedia`, `ReviewQuestionCard`, `Button`, `Card`.
- The "correct?" verdict is all-or-nothing (selected set exactly equals the correct-option-id set), computed client-side.
- Run backend commands from `backend/` (venv active, postgres+redis up); frontend from `frontend/`.

---

### Task 1: Backend practice endpoints

**Files:**
- Create: `backend/app/practice_schemas.py`
- Create: `backend/app/routers/practice.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_practice.py`

**Interfaces:**
- Consumes: `get_current_user`, `get_session`, `Question`/`Option` models.
- Produces:
  - `GET /practice/themes` → `list[ThemeCount]` (`{theme: str, count: int}`), distinct themes + counts, ordered by theme.
  - `GET /practice/questions?theme=A&theme=B` → `list[PracticeQuestion]` (theme ∈ provided, shuffled, options include `is_correct`, plus `explanation`); no themes → `[]`.
  - Schemas `ThemeCount`, `PracticeOption`, `PracticeQuestion` in `app/practice_schemas.py`.

- [ ] **Step 1: Create `app/practice_schemas.py`**

```python
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
```

- [ ] **Step 2: Create `app/routers/practice.py`**

```python
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
```

- [ ] **Step 3: Wire the router into `app/main.py`**

Update the routers import to include `practice`:

```python
from app.routers import auth, exam, health, practice
```

And add this line after the exam router include:

```python
app.include_router(practice.router)
```

- [ ] **Step 4: Write the failing tests — `tests/test_practice.py`**

```python
from app.models import Option, Question


def _seed(session, ref, theme, correct="A"):
    q = Question(
        ref=ref, theme=theme, text=f"Q {ref}", media_type="none", explanation=f"Expl {ref}"
    )
    q.options = [
        Option(label=label, text=label, is_correct=(label == correct))
        for label in ["A", "B", "C", "D"]
    ]
    session.add(q)
    session.flush()
    return q


def _login(client, email="practice@example.com"):
    client.post("/auth/register", json={"email": email, "password": "password123"})
    client.post("/auth/login", json={"email": email, "password": "password123"})


def test_themes_requires_auth(client):
    assert client.get("/practice/themes").status_code == 401


def test_themes_lists_counts(client, session):
    _seed(session, "P1", "panneaux")
    _seed(session, "P2", "panneaux")
    _seed(session, "V1", "vitesse")
    _login(client)
    resp = client.get("/practice/themes")
    assert resp.status_code == 200
    data = {t["theme"]: t["count"] for t in resp.json()}
    assert data == {"panneaux": 2, "vitesse": 1}


def test_questions_filters_by_theme_and_exposes_answers(client, session):
    _seed(session, "P1", "panneaux", correct="B")
    _seed(session, "V1", "vitesse")
    _login(client)
    resp = client.get("/practice/questions", params={"theme": ["panneaux"]})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    q = body[0]
    assert q["theme"] == "panneaux"
    assert q["explanation"] == "Expl P1"
    assert [o["label"] for o in q["options"] if o["is_correct"]] == ["B"]


def test_questions_accepts_multiple_themes(client, session):
    _seed(session, "P1", "panneaux")
    _seed(session, "V1", "vitesse")
    _seed(session, "PR1", "priorités")
    _login(client)
    resp = client.get(
        "/practice/questions", params={"theme": ["panneaux", "vitesse"]}
    )
    assert resp.status_code == 200
    assert {q["theme"] for q in resp.json()} == {"panneaux", "vitesse"}
    assert len(resp.json()) == 2


def test_questions_no_theme_returns_empty(client, session):
    _seed(session, "P1", "panneaux")
    _login(client)
    assert client.get("/practice/questions").json() == []


def test_questions_requires_auth(client):
    assert client.get("/practice/questions", params={"theme": ["x"]}).status_code == 401
```

- [ ] **Step 5: Run the tests (from `backend/`, venv active, postgres+redis up)**

Run: `pytest tests/test_practice.py -v`
Expected: 6 tests PASS.

- [ ] **Step 6: Run the full backend suite**

Run: `pytest -q`
Expected: all pass (no regressions).

- [ ] **Step 7: Commit**

```bash
git add backend/app/practice_schemas.py backend/app/routers/practice.py backend/app/main.py backend/tests/test_practice.py
git commit -m "feat(backend): add training-mode practice endpoints (themes + questions)"
```

---

### Task 2: Frontend practice API-client methods

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/api.practice.test.ts`

**Interfaces:**
- Produces (in `lib/api.ts`): types `ThemeCount`, `PracticeOption`, `PracticeQuestion`; functions `getPracticeThemes()`, `getPracticeQuestions(themes)`.

- [ ] **Step 1: Append types + functions to `frontend/src/lib/api.ts`**

Add at the end of the file (existing code unchanged):

```typescript
export type ThemeCount = { theme: string; count: number };

export type PracticeOption = {
  id: number;
  label: string;
  text: string;
  is_correct: boolean;
};

export type PracticeQuestion = {
  id: number;
  theme: string;
  text: string;
  media_path: string | null;
  media_type: string;
  explanation: string;
  options: PracticeOption[];
};

export function getPracticeThemes(): Promise<ThemeCount[]> {
  return request<ThemeCount[]>("/practice/themes");
}

export function getPracticeQuestions(
  themes: string[],
): Promise<PracticeQuestion[]> {
  const query = themes
    .map((t) => `theme=${encodeURIComponent(t)}`)
    .join("&");
  return request<PracticeQuestion[]>(`/practice/questions?${query}`);
}
```

- [ ] **Step 2: Write the test — `frontend/src/lib/api.practice.test.ts`**

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import { getPracticeQuestions, getPracticeThemes } from "./api";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => body,
  });
}

afterEach(() => vi.restoreAllMocks());

describe("practice api", () => {
  it("getPracticeThemes GETs /practice/themes", async () => {
    const fetchMock = mockFetch(200, [{ theme: "panneaux", count: 3 }]);
    vi.stubGlobal("fetch", fetchMock);
    const res = await getPracticeThemes();
    expect(res).toEqual([{ theme: "panneaux", count: 3 }]);
    expect(fetchMock.mock.calls[0][0]).toContain("/practice/themes");
  });

  it("getPracticeQuestions builds repeated, encoded theme params", async () => {
    const fetchMock = mockFetch(200, []);
    vi.stubGlobal("fetch", fetchMock);
    await getPracticeQuestions(["panneaux", "priorités"]);
    const url = fetchMock.mock.calls[0][0] as string;
    expect(url).toContain(
      "/practice/questions?theme=panneaux&theme=priorit%C3%A9s",
    );
    expect(fetchMock.mock.calls[0][1].credentials).toBe("include");
  });
});
```

- [ ] **Step 3: Verify (nvm first)**

Run: `npm test -- api.practice`, then `npm run lint` (exit 0), then `npm run build`.
Expected: practice api tests PASS; lint exit 0; build clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/api.practice.test.ts
git commit -m "feat(frontend): add practice api-client methods and types"
```

---

### Task 3: `PracticeRunner` component (untimed, reveal-on-Vérifier)

**Files:**
- Create: `frontend/src/components/practice/PracticeRunner.tsx`
- Create: `frontend/src/components/practice/PracticeRunner.test.tsx`

**Interfaces:**
- Consumes: `PracticeQuestion`/`ReviewQuestion` types (`lib/api.ts`), `OptionCard`, `QuestionMedia`, `ReviewQuestionCard`, `Button`, `Card`.
- Produces: `PracticeRunner({ questions: PracticeQuestion[]; onFinish: () => void })` — untimed; per question select → "Vérifier" reveals correction (reusing `ReviewQuestionCard`) → "Suivant"/"Terminer" (last calls `onFinish`).

- [ ] **Step 1: Create `frontend/src/components/practice/PracticeRunner.tsx`**

```tsx
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { OptionCard } from "@/components/exam/OptionCard";
import { QuestionMedia } from "@/components/exam/QuestionMedia";
import { ReviewQuestionCard } from "@/components/exam/ReviewQuestionCard";
import type { PracticeQuestion, ReviewQuestion } from "@/lib/api";

export function PracticeRunner({
  questions,
  onFinish,
}: {
  questions: PracticeQuestion[];
  onFinish: () => void;
}) {
  const [index, setIndex] = useState(0);
  const [selected, setSelected] = useState<number[]>([]);
  const [revealed, setRevealed] = useState(false);

  if (questions.length === 0) {
    return (
      <Card className="text-center text-slate-600">
        Aucune question pour ces thèmes.{" "}
        <button
          onClick={onFinish}
          className="font-semibold text-indigo-700 hover:underline"
        >
          Retour
        </button>
      </Card>
    );
  }

  const question = questions[index];
  const isLast = index + 1 === questions.length;

  function toggle(optionId: number) {
    if (revealed) return;
    setSelected((prev) =>
      prev.includes(optionId)
        ? prev.filter((id) => id !== optionId)
        : [...prev, optionId],
    );
  }

  function next() {
    if (isLast) {
      onFinish();
      return;
    }
    setIndex((i) => i + 1);
    setSelected([]);
    setRevealed(false);
  }

  const correctIds = new Set(
    question.options.filter((o) => o.is_correct).map((o) => o.id),
  );
  const selectedSet = new Set(selected);
  const isCorrect =
    selectedSet.size === correctIds.size &&
    [...selectedSet].every((id) => correctIds.has(id));

  const reviewQuestion: ReviewQuestion = {
    id: question.id,
    theme: question.theme,
    text: question.text,
    media_path: question.media_path,
    media_type: question.media_type,
    explanation: question.explanation,
    options: question.options,
    selected_option_ids: selected,
    is_correct: isCorrect,
  };

  return (
    <div className="space-y-4">
      <p className="text-sm font-medium text-slate-600">
        Question {index + 1} / {questions.length}
      </p>
      {revealed ? (
        <ReviewQuestionCard question={reviewQuestion} index={index} />
      ) : (
        <Card className="space-y-4">
          <span className="w-fit rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
            {question.theme}
          </span>
          <h1 className="text-lg font-semibold text-slate-900">{question.text}</h1>
          <QuestionMedia
            mediaType={question.media_type}
            mediaPath={question.media_path}
          />
          <div className="space-y-2">
            {question.options.map((opt) => (
              <OptionCard
                key={opt.id}
                option={opt}
                selected={selected.includes(opt.id)}
                onToggle={() => toggle(opt.id)}
              />
            ))}
          </div>
        </Card>
      )}
      <div className="flex justify-end">
        {revealed ? (
          <Button onClick={next}>{isLast ? "Terminer" : "Suivant"}</Button>
        ) : (
          <Button onClick={() => setRevealed(true)} disabled={selected.length === 0}>
            Vérifier
          </Button>
        )}
      </div>
    </div>
  );
}
```

Note: `PracticeOption` and `ReviewOption` have identical shapes, so `question.options` is assignable to `ReviewQuestion.options`; `OptionCard` expects `{id,label,text}` and a `PracticeOption` (which additionally has `is_correct`) is structurally compatible.

- [ ] **Step 2: Write the test — `frontend/src/components/practice/PracticeRunner.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PracticeRunner } from "./PracticeRunner";
import type { PracticeQuestion } from "@/lib/api";

const questions: PracticeQuestion[] = [
  {
    id: 1, theme: "panneaux", text: "Q1 ?", media_path: null, media_type: "none",
    explanation: "Explication 1",
    options: [
      { id: 1, label: "A", text: "Bonne", is_correct: true },
      { id: 2, label: "B", text: "Mauvaise", is_correct: false },
    ],
  },
  {
    id: 2, theme: "vitesse", text: "Q2 ?", media_path: null, media_type: "none",
    explanation: "Explication 2",
    options: [
      { id: 3, label: "A", text: "A", is_correct: false },
      { id: 4, label: "B", text: "B", is_correct: true },
    ],
  },
];

describe("PracticeRunner", () => {
  it("has no timer/countdown", () => {
    render(<PracticeRunner questions={questions} onFinish={() => {}} />);
    expect(screen.queryByText(/Temps restant/)).not.toBeInTheDocument();
  });

  it("reveals explanation + verdict after Vérifier, then advances on Suivant", async () => {
    render(<PracticeRunner questions={questions} onFinish={() => {}} />);
    expect(screen.getByText("Q1 ?")).toBeInTheDocument();
    const verify = screen.getByRole("button", { name: "Vérifier" });
    expect(verify).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /Bonne/ }));
    await userEvent.click(verify);
    expect(screen.getByText("Explication 1")).toBeInTheDocument();
    expect(screen.getByText("Correct")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Suivant" }));
    expect(screen.getByText("Q2 ?")).toBeInTheDocument();
  });

  it("shows Terminer on the last question and calls onFinish", async () => {
    const onFinish = vi.fn();
    render(<PracticeRunner questions={[questions[0]]} onFinish={onFinish} />);
    await userEvent.click(screen.getByRole("button", { name: /Bonne/ }));
    await userEvent.click(screen.getByRole("button", { name: "Vérifier" }));
    await userEvent.click(screen.getByRole("button", { name: "Terminer" }));
    expect(onFinish).toHaveBeenCalledOnce();
  });
});
```

- [ ] **Step 3: Verify (nvm first)**

Run: `npm test -- PracticeRunner`, then `npm run lint` (exit 0), then `npm run build`.
Expected: PracticeRunner tests PASS; lint exit 0; build clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/practice/
git commit -m "feat(frontend): add untimed practice runner with reveal-on-verify"
```

---

### Task 4: `/practice` page and dashboard entry

**Files:**
- Create: `frontend/src/app/practice/page.tsx`
- Modify: `frontend/src/app/page.tsx` (add the "Mode entraînement" card)
- Create: `frontend/src/app/practice/page.test.tsx`

**Interfaces:**
- Consumes: `getPracticeThemes`/`getPracticeQuestions` (Task 2), `PracticeRunner` (Task 3), `RequireAuth`/`TopBar`/`Button`/`Card`.
- Produces: `/practice` route (theme multi-select → runner); a dashboard card linking to `/practice`.

- [ ] **Step 1: Create `frontend/src/app/practice/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { RequireAuth } from "@/components/RequireAuth";
import { TopBar } from "@/components/TopBar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PracticeRunner } from "@/components/practice/PracticeRunner";
import * as api from "@/lib/api";
import type { PracticeQuestion, ThemeCount } from "@/lib/api";

function PracticeView() {
  const [themes, setThemes] = useState<ThemeCount[] | null>(null);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [questions, setQuestions] = useState<PracticeQuestion[] | null>(null);
  const [loadingQuestions, setLoadingQuestions] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await api.getPracticeThemes();
        if (active) setThemes(data);
      } catch {
        if (active) setError("Impossible de charger les thèmes.");
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  function toggleTheme(theme: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(theme)) next.delete(theme);
      else next.add(theme);
      return next;
    });
  }

  function toggleAll() {
    if (!themes) return;
    setSelected((prev) =>
      prev.size === themes.length
        ? new Set()
        : new Set(themes.map((t) => t.theme)),
    );
  }

  async function start() {
    setLoadingQuestions(true);
    try {
      const qs = await api.getPracticeQuestions([...selected]);
      setQuestions(qs);
    } catch {
      setError("Impossible de charger les questions.");
    } finally {
      setLoadingQuestions(false);
    }
  }

  if (questions !== null) {
    return (
      <main className="mx-auto max-w-2xl px-4 py-8">
        <PracticeRunner
          questions={questions}
          onFinish={() => {
            setQuestions(null);
            setSelected(new Set());
          }}
        />
      </main>
    );
  }

  if (error) {
    return <p className="px-4 py-10 text-center text-slate-600">{error}</p>;
  }
  if (!themes) {
    return <p className="px-4 py-10 text-center text-slate-500">Chargement…</p>;
  }

  return (
    <main className="mx-auto max-w-2xl space-y-4 px-4 py-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Mode entraînement</h1>
        <p className="text-slate-600">Choisissez un ou plusieurs thèmes.</p>
      </div>
      {themes.length === 0 ? (
        <Card className="text-center text-slate-600">
          Aucune question disponible pour l&apos;instant.
        </Card>
      ) : (
        <>
          <button
            type="button"
            onClick={toggleAll}
            className="text-sm font-semibold text-indigo-700 hover:underline"
          >
            {selected.size === themes.length
              ? "Tout désélectionner"
              : "Tout sélectionner"}
          </button>
          <ul className="space-y-2">
            {themes.map((t) => {
              const isSel = selected.has(t.theme);
              return (
                <li key={t.theme}>
                  <button
                    type="button"
                    onClick={() => toggleTheme(t.theme)}
                    aria-pressed={isSel}
                    className={`flex w-full items-center justify-between rounded-xl border p-4 text-left transition-colors ${
                      isSel
                        ? "border-indigo-600 bg-indigo-50 ring-1 ring-indigo-600"
                        : "border-slate-200 bg-white hover:bg-slate-50"
                    }`}
                  >
                    <span className="font-medium capitalize text-slate-900">
                      {t.theme}
                    </span>
                    <span className="text-sm text-slate-500">
                      {t.count} question{t.count > 1 ? "s" : ""}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
          <div className="flex justify-end">
            <Button
              onClick={start}
              disabled={selected.size === 0 || loadingQuestions}
            >
              {loadingQuestions ? "…" : "Commencer"}
            </Button>
          </div>
        </>
      )}
    </main>
  );
}

export default function PracticePage() {
  return (
    <RequireAuth>
      <TopBar />
      <PracticeView />
    </RequireAuth>
  );
}
```

- [ ] **Step 2: Add the "Mode entraînement" card to `frontend/src/app/page.tsx`**

In the dashboard's card grid (the `<div className="mt-8 grid gap-4 sm:grid-cols-2">` block), add a third `Card` after the existing "Mon historique" card:

```tsx
          <Card className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold text-slate-900">Mode entraînement</h2>
            <p className="text-sm text-slate-600">
              Entraînez-vous par thème, sans chrono, avec les corrections.
            </p>
            <Link href="/practice" className="mt-auto">
              <Button variant="secondary" className="w-full">
                S&apos;entraîner
              </Button>
            </Link>
          </Card>
```

(`Card`, `Button`, and `Link` are already imported in `page.tsx`.)

- [ ] **Step 3: Write the test — `frontend/src/app/practice/page.test.tsx`**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import PracticePage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

beforeEach(() =>
  vi.spyOn(api, "getMe").mockResolvedValue({ id: 1, email: "a@b.com" }),
);
afterEach(() => vi.restoreAllMocks());

function renderPractice() {
  return render(
    <AuthProvider>
      <PracticePage />
    </AuthProvider>,
  );
}

describe("PracticePage", () => {
  it("lists themes and enables Commencer only once a theme is selected", async () => {
    vi.spyOn(api, "getPracticeThemes").mockResolvedValue([
      { theme: "panneaux", count: 3 },
      { theme: "vitesse", count: 2 },
    ]);
    renderPractice();
    expect(await screen.findByText("panneaux")).toBeInTheDocument();
    const commencer = screen.getByRole("button", { name: "Commencer" });
    expect(commencer).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /panneaux/ }));
    expect(commencer).toBeEnabled();
  });

  it("starts a session with the selected themes and shows the first question", async () => {
    vi.spyOn(api, "getPracticeThemes").mockResolvedValue([
      { theme: "panneaux", count: 1 },
    ]);
    const getQs = vi.spyOn(api, "getPracticeQuestions").mockResolvedValue([
      {
        id: 1, theme: "panneaux", text: "Question test ?", media_path: null,
        media_type: "none", explanation: "Expl",
        options: [
          { id: 1, label: "A", text: "A", is_correct: true },
          { id: 2, label: "B", text: "B", is_correct: false },
        ],
      },
    ]);
    renderPractice();
    await userEvent.click(await screen.findByRole("button", { name: /panneaux/ }));
    await userEvent.click(screen.getByRole("button", { name: "Commencer" }));
    await waitFor(() =>
      expect(screen.getByText("Question test ?")).toBeInTheDocument(),
    );
    expect(getQs).toHaveBeenCalledWith(["panneaux"]);
  });
});
```

- [ ] **Step 4: Verify (nvm first)**

Run: `npm test` (all pass), `npm run lint` (exit 0), `npm run build` (clean; `/practice` compiles).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/practice/ frontend/src/app/page.tsx
git commit -m "feat(frontend): add training-mode page with theme selection and dashboard entry"
```

---

## Controller verification (live, after Task 4)

Not a subagent task — the controller runs backend + frontend and walks the flow: dashboard → "S'entraîner" → select theme(s) → start → answer a question → "Vérifier" reveals the correct answer + explanation (no timer) → "Suivant"/"Terminer" → back to theme selection. Confirms the untimed reveal flow works against the real API + placeholder bank.

## Self-Review

**Spec coverage:**
- No timer, per-question reveal after validate → Task 3 (`PracticeRunner`). ✓
- Theme-filtered, multi-theme selection → Task 1 (endpoints) + Task 4 (multi-select page). ✓
- Ephemeral (no attempt/score/history) → nothing persists; no attempt code anywhere. ✓
- Backend `/practice/themes` + `/practice/questions` with answer keys + explanations → Task 1. ✓
- Dashboard "Mode entraînement" entry → Task 4. ✓
- Reuse `OptionCard`/`QuestionMedia`/`ReviewQuestionCard` → Task 3. ✓
- Auth + read-only endpoints, no DB change → Task 1. ✓
- All-or-nothing verdict client-side → Task 3. ✓

**Placeholder scan:** No TBDs; all code + tests concrete.

**Type consistency:** `ThemeCount`/`PracticeOption`/`PracticeQuestion` defined in Task 1 (backend) and Task 2 (frontend) with matching field names; `getPracticeThemes`/`getPracticeQuestions(themes: string[])` defined Task 2, consumed Task 4; `PracticeRunner({questions, onFinish})` defined Task 3, consumed Task 4; the `ReviewQuestion` shape built in Task 3 matches the existing `ReviewQuestionCard` prop.

**Deferred:** real content population; Phase 5 polish.
