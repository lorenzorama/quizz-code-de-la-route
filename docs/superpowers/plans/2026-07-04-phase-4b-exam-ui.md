# Phase 4b — Exam Experience UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the exam-simulation UI on the Phase 4a foundation: a timed runner (20s/question, auto-advance, no going back), a per-question review with correct answers + explanations + media, and an attempt history — all in the indigo/light design system, wired to the Phase 3 exam API.

**Architecture:** New exam API-client methods + types in `lib/api.ts`. A dedicated `useCountdown` hook isolates timer state (per the Phase 4a review). Presentational components (`Countdown`, `ProgressIndicator`, `OptionCard`, `QuestionMedia`, `ScoreBanner`) render one concern each. The runner page (`/exam`) owns the exam state machine (load → per-question select/advance → submit → navigate). The review page (`/exam/[attemptId]/review`) shows the score banner + full review; history (`/history`) lists attempts linking to their review. All pages are wrapped in the existing `RequireAuth` guard.

**Tech Stack:** Next.js App Router + React + TypeScript, Tailwind (indigo/light), Vitest + RTL (fake timers for the countdown), the Phase 3 `/exam/*` API.

## Global Constraints

- Run frontend commands from `frontend/`. **Node ≥ 20.19 required** — before any npm command: `export NVM_DIR="$HOME/.nvm"; . "$NVM_DIR/nvm.sh"; cd frontend && nvm use` (`.nvmrc` → v20.20.2). node_modules already installed; do NOT reinstall.
- `npm run lint` must stay at **exit 0**, `npm test` all pass, `npm run build` clean — every task verifies all three before its commit.
- Design system (indigo/light, from Phase 4a): reuse `Button`/`Card`/`Field`/`Input`; indigo-600 primary, slate neutrals, `emerald-600` = correct, `red-600` = wrong, amber for the timer running low; Inter font; French copy; responsive; accessible (roles, labels, focus, `aria-live` where state changes).
- All exam pages wrapped in `RequireAuth`; use `Depends`-authenticated API calls (cookie auth already works).
- Timer state lives in the `useCountdown` hook; reset per question via the React `key` remount pattern (NOT `setState` inside an effect — keep the lint gate green).
- Exam flow is one-way: no "previous" control; advancing (manual "Suivant" or 20s timeout) is irreversible. On timeout the current selection (possibly empty) is recorded and the runner advances; after the last question it submits.
- Media: backend serves files at `<API_BASE_URL>/media/<media_path>`. Use a plain `<img>`/`<video>` (not `next/image`, to avoid remote-domain config). `media_type` is `image` | `video` | `none`.
- `useCountdown` and timer tests use `vi.useFakeTimers()` — never real waits.

---

### Task 1: Exam API-client methods, types, and media URL helper

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/api.exam.test.ts`

**Interfaces:**
- Produces (in `lib/api.ts`): types `ExamOption`, `ExamQuestion`, `StartExamResponse`, `SubmittedAnswer`, `ExamResult`, `ReviewOption`, `ReviewQuestion`, `Review`, `AttemptSummary`; functions `startExam()`, `submitExam(attemptId, answers)`, `getReview(attemptId)`, `getHistory()`; helper `mediaUrl(path)`.

- [ ] **Step 1: Append types + functions + `mediaUrl` to `frontend/src/lib/api.ts`**

Add at the end of the file (the existing `request<T>`, `BASE_URL`, `ApiError`, `User` remain unchanged):

```typescript
export type ExamOption = { id: number; label: string; text: string };

export type ExamQuestion = {
  id: number;
  theme: string;
  text: string;
  media_path: string | null;
  media_type: string;
  options: ExamOption[];
};

export type StartExamResponse = {
  attempt_id: number;
  question_count: number;
  questions: ExamQuestion[];
};

export type SubmittedAnswer = {
  question_id: number;
  selected_option_ids: number[];
  time_taken?: number | null;
};

export type ExamResult = {
  attempt_id: number;
  score: number;
  total: number;
  passed: boolean;
};

export type ReviewOption = {
  id: number;
  label: string;
  text: string;
  is_correct: boolean;
};

export type ReviewQuestion = {
  id: number;
  theme: string;
  text: string;
  media_path: string | null;
  media_type: string;
  explanation: string;
  options: ReviewOption[];
  selected_option_ids: number[];
  is_correct: boolean;
};

export type Review = {
  attempt_id: number;
  score: number;
  total: number;
  passed: boolean;
  questions: ReviewQuestion[];
};

export type AttemptSummary = {
  id: number;
  started_at: string;
  finished_at: string | null;
  score: number | null;
  passed: boolean | null;
  status: string;
};

export function startExam(): Promise<StartExamResponse> {
  return request<StartExamResponse>("/exam/start", { method: "POST" });
}

export function submitExam(
  attemptId: number,
  answers: SubmittedAnswer[],
): Promise<ExamResult> {
  return request<ExamResult>(`/exam/${attemptId}/submit`, {
    method: "POST",
    body: JSON.stringify({ answers }),
  });
}

export function getReview(attemptId: number): Promise<Review> {
  return request<Review>(`/exam/${attemptId}/review`);
}

export function getHistory(): Promise<AttemptSummary[]> {
  return request<AttemptSummary[]>("/exam/history");
}

export function mediaUrl(path: string): string {
  return `${BASE_URL}/media/${path}`;
}
```

- [ ] **Step 2: Write the test — `frontend/src/lib/api.exam.test.ts`**

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import { getHistory, getReview, mediaUrl, startExam, submitExam } from "./api";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => body,
  });
}

afterEach(() => vi.restoreAllMocks());

describe("exam api", () => {
  it("startExam POSTs to /exam/start", async () => {
    const fetchMock = mockFetch(201, { attempt_id: 5, question_count: 0, questions: [] });
    vi.stubGlobal("fetch", fetchMock);
    const res = await startExam();
    expect(res.attempt_id).toBe(5);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/exam/start");
    expect(options.method).toBe("POST");
    expect(options.credentials).toBe("include");
  });

  it("submitExam POSTs answers to the attempt", async () => {
    const fetchMock = mockFetch(200, { attempt_id: 5, score: 2, total: 3, passed: false });
    vi.stubGlobal("fetch", fetchMock);
    const res = await submitExam(5, [{ question_id: 1, selected_option_ids: [10] }]);
    expect(res.score).toBe(2);
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toContain("/exam/5/submit");
    expect(JSON.parse(options.body)).toEqual({
      answers: [{ question_id: 1, selected_option_ids: [10] }],
    });
  });

  it("getReview GETs the review", async () => {
    const fetchMock = mockFetch(200, {
      attempt_id: 5, score: 3, total: 3, passed: true, questions: [],
    });
    vi.stubGlobal("fetch", fetchMock);
    const res = await getReview(5);
    expect(res.passed).toBe(true);
    expect(fetchMock.mock.calls[0][0]).toContain("/exam/5/review");
  });

  it("getHistory GETs the history list", async () => {
    const fetchMock = mockFetch(200, [{ id: 1, started_at: "x", finished_at: null, score: null, passed: null, status: "in_progress" }]);
    vi.stubGlobal("fetch", fetchMock);
    const res = await getHistory();
    expect(res).toHaveLength(1);
    expect(fetchMock.mock.calls[0][0]).toContain("/exam/history");
  });

  it("mediaUrl builds an absolute media URL", () => {
    expect(mediaUrl("signs/q1.jpg")).toMatch(/\/media\/signs\/q1\.jpg$/);
  });
});
```

- [ ] **Step 3: Verify (nvm first)**

Run: `npm test -- api.exam` then `npm run lint` (exit 0) and `npm run build`.
Expected: exam api tests PASS; lint exit 0; build clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/api.exam.test.ts
git commit -m "feat(frontend): add exam api-client methods, types, and media URL helper"
```

---

### Task 2: `useCountdown` hook and exam presentational components

**Files:**
- Create: `frontend/src/lib/useCountdown.ts`
- Create: `frontend/src/components/exam/Countdown.tsx`
- Create: `frontend/src/components/exam/ProgressIndicator.tsx`
- Create: `frontend/src/components/exam/OptionCard.tsx`
- Create: `frontend/src/components/exam/QuestionMedia.tsx`
- Create: `frontend/src/components/exam/ScoreBanner.tsx`
- Create: `frontend/src/lib/useCountdown.test.ts`
- Create: `frontend/src/components/exam/OptionCard.test.tsx`
- Create: `frontend/src/components/exam/ScoreBanner.test.tsx`

**Interfaces:**
- Produces:
  - `useCountdown(seconds: number, onExpire: () => void): number` — returns remaining seconds; decrements each second; calls `onExpire` once at 0. Reset by remounting the consumer via a React `key`.
  - `Countdown({ seconds, onExpire })` — visual bar + numeric seconds; goes amber ≤ 5s.
  - `ProgressIndicator({ current, total })` — "Question X / Y" + a progress bar.
  - `OptionCard({ option, selected, onToggle })` — clickable A–D option with selected state.
  - `QuestionMedia({ mediaType, mediaPath })` — renders image/video/none.
  - `ScoreBanner({ score, total, passed })` — big score + pass/fail state.

- [ ] **Step 1: Create `frontend/src/lib/useCountdown.ts`**

```typescript
"use client";

import { useEffect, useRef, useState } from "react";

export function useCountdown(seconds: number, onExpire: () => void): number {
  const [remaining, setRemaining] = useState(seconds);
  const onExpireRef = useRef(onExpire);
  onExpireRef.current = onExpire;

  useEffect(() => {
    if (remaining <= 0) {
      onExpireRef.current();
      return;
    }
    const id = setTimeout(() => setRemaining((r) => r - 1), 1000);
    return () => clearTimeout(id);
  }, [remaining]);

  return remaining;
}
```

Note: no `setState` directly in an effect (keeps the lint gate green). The decrement runs inside the `setTimeout` callback; `onExpire` fires from the `remaining <= 0` branch. Reset between questions is done by the parent passing a changing `key` to the `Countdown` component, which remounts it and re-runs `useState(seconds)`.

- [ ] **Step 2: Create `frontend/src/components/exam/Countdown.tsx`**

```tsx
"use client";

import { useCountdown } from "@/lib/useCountdown";

export function Countdown({
  seconds,
  onExpire,
}: {
  seconds: number;
  onExpire: () => void;
}) {
  const remaining = useCountdown(seconds, onExpire);
  const pct = Math.max(0, Math.round((remaining / seconds) * 100));
  const low = remaining <= 5;

  return (
    <div className="space-y-1" aria-live="polite">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-slate-600">Temps restant</span>
        <span
          className={`font-semibold tabular-nums ${low ? "text-red-600" : "text-slate-900"}`}
        >
          {remaining}s
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-full rounded-full transition-[width] duration-1000 ease-linear ${low ? "bg-red-500" : "bg-indigo-600"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create `frontend/src/components/exam/ProgressIndicator.tsx`**

```tsx
export function ProgressIndicator({
  current,
  total,
}: {
  current: number;
  total: number;
}) {
  const pct = Math.round((current / total) * 100);
  return (
    <div className="space-y-1">
      <p className="text-sm font-medium text-slate-600">
        Question {current} / {total}
      </p>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
        <div className="h-full rounded-full bg-indigo-600" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create `frontend/src/components/exam/OptionCard.tsx`**

```tsx
"use client";

import { ExamOption } from "@/lib/api";

export function OptionCard({
  option,
  selected,
  onToggle,
}: {
  option: ExamOption;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={selected}
      className={`flex w-full items-center gap-3 rounded-xl border p-4 text-left transition-colors ${
        selected
          ? "border-indigo-600 bg-indigo-50 ring-1 ring-indigo-600"
          : "border-slate-200 bg-white hover:bg-slate-50"
      }`}
    >
      <span
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold ${
          selected ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-700"
        }`}
      >
        {option.label}
      </span>
      <span className="text-sm text-slate-900">{option.text}</span>
    </button>
  );
}
```

- [ ] **Step 5: Create `frontend/src/components/exam/QuestionMedia.tsx`**

```tsx
import { mediaUrl } from "@/lib/api";

export function QuestionMedia({
  mediaType,
  mediaPath,
}: {
  mediaType: string;
  mediaPath: string | null;
}) {
  if (!mediaPath || mediaType === "none") return null;
  const src = mediaUrl(mediaPath);

  if (mediaType === "video") {
    return (
      <video
        controls
        src={src}
        className="w-full rounded-xl border border-slate-200 bg-black"
      />
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={src}
      alt="Illustration de la question"
      className="w-full rounded-xl border border-slate-200 object-cover"
    />
  );
}
```

- [ ] **Step 6: Create `frontend/src/components/exam/ScoreBanner.tsx`**

```tsx
export function ScoreBanner({
  score,
  total,
  passed,
}: {
  score: number;
  total: number;
  passed: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-6 text-center ${
        passed ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50"
      }`}
    >
      <p className="text-sm font-medium text-slate-600">Votre score</p>
      <p className="mt-1 text-4xl font-bold text-slate-900">
        {score}
        <span className="text-2xl text-slate-400"> / {total}</span>
      </p>
      <p
        className={`mt-2 text-lg font-semibold ${
          passed ? "text-emerald-700" : "text-red-700"
        }`}
      >
        {passed ? "Réussi ✅" : "Échoué ❌"}
      </p>
    </div>
  );
}
```

- [ ] **Step 7: Write the hook test — `frontend/src/lib/useCountdown.test.ts`**

```typescript
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useCountdown } from "./useCountdown";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("useCountdown", () => {
  it("counts down each second", () => {
    const { result } = renderHook(() => useCountdown(3, () => {}));
    expect(result.current).toBe(3);
    act(() => vi.advanceTimersByTime(1000));
    expect(result.current).toBe(2);
    act(() => vi.advanceTimersByTime(2000));
    expect(result.current).toBe(0);
  });

  it("calls onExpire once when it reaches zero", () => {
    const onExpire = vi.fn();
    renderHook(() => useCountdown(2, onExpire));
    act(() => vi.advanceTimersByTime(2000));
    expect(onExpire).toHaveBeenCalledTimes(1);
    act(() => vi.advanceTimersByTime(2000));
    expect(onExpire).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 8: Write the OptionCard test — `frontend/src/components/exam/OptionCard.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { OptionCard } from "./OptionCard";

const option = { id: 1, label: "A", text: "Priorité à droite" };

describe("OptionCard", () => {
  it("shows label + text and toggles on click", async () => {
    const onToggle = vi.fn();
    render(<OptionCard option={option} selected={false} onToggle={onToggle} />);
    const btn = screen.getByRole("button", { name: /Priorité à droite/ });
    expect(btn).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(btn);
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it("reflects the selected state via aria-pressed", () => {
    render(<OptionCard option={option} selected onToggle={() => {}} />);
    expect(screen.getByRole("button", { name: /Priorité à droite/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
```

- [ ] **Step 9: Write the ScoreBanner test — `frontend/src/components/exam/ScoreBanner.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ScoreBanner } from "./ScoreBanner";

describe("ScoreBanner", () => {
  it("shows a passing state", () => {
    render(<ScoreBanner score={38} total={40} passed />);
    expect(screen.getByText("/ 40")).toBeInTheDocument();
    expect(screen.getByText(/Réussi/)).toBeInTheDocument();
  });

  it("shows a failing state", () => {
    render(<ScoreBanner score={20} total={40} passed={false} />);
    expect(screen.getByText(/Échoué/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 10: Verify (nvm first)**

Run: `npm test` (all pass, incl. countdown/OptionCard/ScoreBanner), `npm run lint` (exit 0), `npm run build`.

- [ ] **Step 11: Commit**

```bash
git add frontend/src/lib/useCountdown.ts frontend/src/lib/useCountdown.test.ts frontend/src/components/exam/
git commit -m "feat(frontend): add countdown hook and exam UI components"
```

---

### Task 3: Exam runner page (`/exam`)

**Files:**
- Create: `frontend/src/app/exam/page.tsx`
- Create: `frontend/src/app/exam/page.test.tsx`

**Interfaces:**
- Consumes: `startExam`/`submitExam` (Task 1), `Countdown`/`ProgressIndicator`/`OptionCard`/`QuestionMedia` (Task 2), `RequireAuth`/`TopBar`/`Button`/`Card` (Phase 4a).
- Produces: `/exam` route — loads an attempt, runs the timed one-way flow, submits, and navigates to `/exam/<attemptId>/review`.

- [ ] **Step 1: Create `frontend/src/app/exam/page.tsx`**

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { TopBar } from "@/components/TopBar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Countdown } from "@/components/exam/Countdown";
import { OptionCard } from "@/components/exam/OptionCard";
import { ProgressIndicator } from "@/components/exam/ProgressIndicator";
import { QuestionMedia } from "@/components/exam/QuestionMedia";
import * as api from "@/lib/api";
import type { ExamQuestion, SubmittedAnswer } from "@/lib/api";

const SECONDS_PER_QUESTION = 20;

function Runner() {
  const router = useRouter();
  const [phase, setPhase] = useState<"loading" | "error" | "running" | "submitting">(
    "loading",
  );
  const [errorMsg, setErrorMsg] = useState("");
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [questions, setQuestions] = useState<ExamQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const answersRef = useRef<SubmittedAnswer[]>([]);
  const startedAtRef = useRef<number>(0);
  const [selected, setSelected] = useState<number[]>([]);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const res = await api.startExam();
        if (!active) return;
        setAttemptId(res.attempt_id);
        setQuestions(res.questions);
        answersRef.current = res.questions.map((q) => ({
          question_id: q.id,
          selected_option_ids: [],
        }));
        startedAtRef.current = timestamp();
        setPhase("running");
      } catch (err) {
        if (!active) return;
        setErrorMsg(
          err instanceof api.ApiError && err.status === 409
            ? "Aucune question disponible pour le moment."
            : "Impossible de démarrer l'examen.",
        );
        setPhase("error");
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  function timestamp(): number {
    return new Date().getTime();
  }

  function toggle(optionId: number) {
    setSelected((prev) =>
      prev.includes(optionId)
        ? prev.filter((id) => id !== optionId)
        : [...prev, optionId],
    );
  }

  async function advance() {
    const elapsed = Math.min(
      SECONDS_PER_QUESTION,
      Math.round((timestamp() - startedAtRef.current) / 1000),
    );
    answersRef.current[index] = {
      question_id: questions[index].id,
      selected_option_ids: selected,
      time_taken: elapsed,
    };

    if (index + 1 < questions.length) {
      setSelected([]);
      startedAtRef.current = timestamp();
      setIndex((i) => i + 1);
      return;
    }

    setPhase("submitting");
    try {
      const result = await api.submitExam(attemptId as number, answersRef.current);
      router.push(`/exam/${result.attempt_id}/review`);
    } catch {
      setErrorMsg("Échec de l'envoi de l'examen. Réessayez.");
      setPhase("error");
    }
  }

  if (phase === "loading") {
    return <Centered>Préparation de l&apos;examen…</Centered>;
  }
  if (phase === "error") {
    return (
      <Centered>
        <p className="text-slate-700">{errorMsg}</p>
        <Link href="/" className="mt-4 inline-block">
          <Button variant="secondary">Retour à l&apos;accueil</Button>
        </Link>
      </Centered>
    );
  }
  if (phase === "submitting") {
    return <Centered>Calcul de votre score…</Centered>;
  }

  const question = questions[index];
  const isLast = index + 1 === questions.length;

  return (
    <main className="mx-auto max-w-2xl space-y-6 px-4 py-8">
      <ProgressIndicator current={index + 1} total={questions.length} />
      <Countdown key={index} seconds={SECONDS_PER_QUESTION} onExpire={advance} />
      <Card className="space-y-4">
        <span className="inline-block rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
          {question.theme}
        </span>
        <h1 className="text-lg font-semibold text-slate-900">{question.text}</h1>
        <QuestionMedia mediaType={question.media_type} mediaPath={question.media_path} />
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
      <div className="flex justify-end">
        <Button onClick={advance}>{isLast ? "Terminer" : "Suivant"}</Button>
      </div>
    </main>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 text-center text-slate-600">
      {children}
    </div>
  );
}

export default function ExamPage() {
  return (
    <RequireAuth>
      <TopBar />
      <Runner />
    </RequireAuth>
  );
}
```

- [ ] **Step 2: Write the test — `frontend/src/app/exam/page.test.tsx`**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import ExamPage from "./page";

const push = vi.fn();
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace: vi.fn() }),
}));

function makeQuestions(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    theme: "priorités",
    text: `Question ${i + 1}`,
    media_path: null,
    media_type: "none",
    options: [
      { id: i * 10 + 1, label: "A", text: "A" },
      { id: i * 10 + 2, label: "B", text: "B" },
    ],
  }));
}

beforeEach(() => {
  push.mockClear();
  vi.spyOn(api, "getMe").mockResolvedValue({ id: 1, email: "a@b.com" });
});
afterEach(() => vi.restoreAllMocks());

function renderExam() {
  return render(
    <AuthProvider>
      <ExamPage />
    </AuthProvider>,
  );
}

describe("ExamPage runner", () => {
  it("shows an error when the bank is empty (409)", async () => {
    vi.spyOn(api, "startExam").mockRejectedValue(new api.ApiError(409, "empty"));
    renderExam();
    expect(await screen.findByText(/Aucune question disponible/)).toBeInTheDocument();
  });

  it("runs through questions, submits selected answers, and navigates to review", async () => {
    const questions = makeQuestions(2);
    vi.spyOn(api, "startExam").mockResolvedValue({
      attempt_id: 42,
      question_count: 2,
      questions,
    });
    const submit = vi
      .spyOn(api, "submitExam")
      .mockResolvedValue({ attempt_id: 42, score: 2, total: 2, passed: true });

    renderExam();

    // Q1: select A, click Suivant
    await screen.findByText("Question 1");
    await userEvent.click(screen.getByRole("button", { name: /^A/ }));
    await userEvent.click(screen.getByRole("button", { name: "Suivant" }));

    // Q2: select B, click Terminer
    await screen.findByText("Question 2");
    await userEvent.click(screen.getByRole("button", { name: /^B/ }));
    await userEvent.click(screen.getByRole("button", { name: "Terminer" }));

    await waitFor(() => expect(submit).toHaveBeenCalledOnce());
    const [attemptId, answers] = submit.mock.calls[0];
    expect(attemptId).toBe(42);
    expect(answers[0].selected_option_ids).toEqual([1]); // Q1 option A id
    expect(answers[1].selected_option_ids).toEqual([12]); // Q2 option B id
    await waitFor(() => expect(push).toHaveBeenCalledWith("/exam/42/review"));
  });

  it("auto-advances when the timer expires", async () => {
    vi.useFakeTimers();
    const questions = makeQuestions(2);
    vi.spyOn(api, "startExam").mockResolvedValue({
      attempt_id: 7,
      question_count: 2,
      questions,
    });
    vi.spyOn(api, "submitExam").mockResolvedValue({
      attempt_id: 7, score: 0, total: 2, passed: false,
    });
    renderExam();
    // flush the startExam microtasks
    await vi.runOnlyPendingTimersAsync();
    expect(screen.getByText("Question 1")).toBeInTheDocument();
    // 20s → auto-advance to Q2
    await vi.advanceTimersByTimeAsync(20000);
    expect(screen.getByText("Question 2")).toBeInTheDocument();
    vi.useRealTimers();
  });
});
```

- [ ] **Step 3: Verify (nvm first)**

Run: `npm test` (all pass), `npm run lint` (exit 0), `npm run build`.
Note: if the fake-timer test is flaky with async `startExam`, prefer `await vi.runOnlyPendingTimersAsync()` after render before advancing (already in the test). If it still can't be made reliable, keep the two non-timer tests and mark the auto-advance one `it.skip` with a `// TODO` — but try to make it pass first.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/app/exam/
git commit -m "feat(frontend): add timed exam runner page"
```

---

### Task 4: Review page and history page

**Files:**
- Create: `frontend/src/app/exam/[attemptId]/review/page.tsx`
- Create: `frontend/src/components/exam/ReviewQuestionCard.tsx`
- Create: `frontend/src/app/history/page.tsx`
- Create: `frontend/src/app/exam/[attemptId]/review/page.test.tsx`
- Create: `frontend/src/app/history/page.test.tsx`

**Interfaces:**
- Consumes: `getReview`/`getHistory` (Task 1), `ScoreBanner`/`QuestionMedia` (Task 2), `RequireAuth`/`TopBar`/`Card`/`Button` (Phase 4a), `useParams` (next/navigation).
- Produces: `/exam/[attemptId]/review` and `/history` routes.

- [ ] **Step 1: Create `frontend/src/components/exam/ReviewQuestionCard.tsx`**

```tsx
import { Card } from "@/components/ui/Card";
import { QuestionMedia } from "@/components/exam/QuestionMedia";
import type { ReviewQuestion } from "@/lib/api";

export function ReviewQuestionCard({
  question,
  index,
}: {
  question: ReviewQuestion;
  index: number;
}) {
  const selected = new Set(question.selected_option_ids);
  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-indigo-700">
          {index + 1}. {question.theme}
        </span>
        <span
          className={`text-sm font-semibold ${question.is_correct ? "text-emerald-700" : "text-red-700"}`}
        >
          {question.is_correct ? "Correct" : "Incorrect"}
        </span>
      </div>
      <h2 className="font-semibold text-slate-900">{question.text}</h2>
      <QuestionMedia mediaType={question.media_type} mediaPath={question.media_path} />
      <ul className="space-y-1.5">
        {question.options.map((opt) => {
          const chosen = selected.has(opt.id);
          const style = opt.is_correct
            ? "border-emerald-300 bg-emerald-50 text-emerald-900"
            : chosen
              ? "border-red-300 bg-red-50 text-red-900"
              : "border-slate-200 text-slate-700";
          return (
            <li
              key={opt.id}
              className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${style}`}
            >
              <span className="font-bold">{opt.label}</span>
              <span>{opt.text}</span>
              {opt.is_correct ? <span className="ml-auto">✓</span> : null}
              {chosen && !opt.is_correct ? <span className="ml-auto">✗</span> : null}
            </li>
          );
        })}
      </ul>
      <div className="rounded-lg bg-slate-50 p-3 text-sm text-slate-700">
        <span className="font-semibold">Explication : </span>
        {question.explanation || "—"}
      </div>
    </Card>
  );
}
```

- [ ] **Step 2: Create `frontend/src/app/exam/[attemptId]/review/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { TopBar } from "@/components/TopBar";
import { Button } from "@/components/ui/Button";
import { ScoreBanner } from "@/components/exam/ScoreBanner";
import { ReviewQuestionCard } from "@/components/exam/ReviewQuestionCard";
import * as api from "@/lib/api";
import type { Review } from "@/lib/api";

function ReviewView() {
  const params = useParams<{ attemptId: string }>();
  const attemptId = Number(params.attemptId);
  const [review, setReview] = useState<Review | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await api.getReview(attemptId);
        if (active) setReview(data);
      } catch {
        if (active) setError("Impossible de charger le corrigé.");
      }
    })();
    return () => {
      active = false;
    };
  }, [attemptId]);

  if (error) {
    return <p className="px-4 py-10 text-center text-slate-600">{error}</p>;
  }
  if (!review) {
    return <p className="px-4 py-10 text-center text-slate-500">Chargement…</p>;
  }

  return (
    <main className="mx-auto max-w-2xl space-y-4 px-4 py-8">
      <ScoreBanner score={review.score} total={review.total} passed={review.passed} />
      <div className="flex justify-between">
        <h1 className="text-xl font-bold text-slate-900">Corrigé</h1>
        <Link href="/">
          <Button variant="secondary">Accueil</Button>
        </Link>
      </div>
      {review.questions.map((q, i) => (
        <ReviewQuestionCard key={q.id} question={q} index={i} />
      ))}
    </main>
  );
}

export default function ReviewPage() {
  return (
    <RequireAuth>
      <TopBar />
      <ReviewView />
    </RequireAuth>
  );
}
```

- [ ] **Step 3: Create `frontend/src/app/history/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { TopBar } from "@/components/TopBar";
import { Card } from "@/components/ui/Card";
import * as api from "@/lib/api";
import type { AttemptSummary } from "@/lib/api";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleDateString("fr-FR");
}

function HistoryView() {
  const [attempts, setAttempts] = useState<AttemptSummary[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const data = await api.getHistory();
        if (active) setAttempts(data);
      } catch {
        if (active) setError("Impossible de charger l'historique.");
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  if (error) return <p className="px-4 py-10 text-center text-slate-600">{error}</p>;
  if (!attempts) return <p className="px-4 py-10 text-center text-slate-500">Chargement…</p>;

  return (
    <main className="mx-auto max-w-2xl space-y-4 px-4 py-8">
      <h1 className="text-2xl font-bold text-slate-900">Mon historique</h1>
      {attempts.length === 0 ? (
        <Card className="text-center text-slate-600">
          Aucun examen pour l&apos;instant.{" "}
          <Link href="/exam" className="font-semibold text-indigo-700 hover:underline">
            Commencer
          </Link>
        </Card>
      ) : (
        <ul className="space-y-3">
          {attempts.map((a) => (
            <li key={a.id}>
              <Card className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-900">{formatDate(a.started_at)}</p>
                  <p className="text-sm text-slate-600">
                    {a.status === "completed"
                      ? `Score ${a.score} / 40`
                      : "En cours / non terminé"}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  {a.status === "completed" ? (
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold ${
                        a.passed
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-red-100 text-red-800"
                      }`}
                    >
                      {a.passed ? "Réussi" : "Échoué"}
                    </span>
                  ) : null}
                  {a.status === "completed" ? (
                    <Link
                      href={`/exam/${a.id}/review`}
                      className="text-sm font-semibold text-indigo-700 hover:underline"
                    >
                      Revoir
                    </Link>
                  ) : null}
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

export default function HistoryPage() {
  return (
    <RequireAuth>
      <TopBar />
      <HistoryView />
    </RequireAuth>
  );
}
```

- [ ] **Step 4: Write the review test — `frontend/src/app/exam/[attemptId]/review/page.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import ReviewPage from "./page";

vi.mock("next/navigation", () => ({
  useParams: () => ({ attemptId: "42" }),
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

beforeEach(() => vi.spyOn(api, "getMe").mockResolvedValue({ id: 1, email: "a@b.com" }));
afterEach(() => vi.restoreAllMocks());

describe("ReviewPage", () => {
  it("shows the score and per-question corrections with explanations", async () => {
    vi.spyOn(api, "getReview").mockResolvedValue({
      attempt_id: 42,
      score: 1,
      total: 1,
      passed: false,
      questions: [
        {
          id: 1,
          theme: "priorités",
          text: "Qui passe ?",
          media_path: null,
          media_type: "none",
          explanation: "Priorité à droite.",
          selected_option_ids: [2],
          is_correct: false,
          options: [
            { id: 1, label: "A", text: "Moi", is_correct: true },
            { id: 2, label: "B", text: "L'autre", is_correct: false },
          ],
        },
      ],
    });
    render(
      <AuthProvider>
        <ReviewPage />
      </AuthProvider>,
    );
    expect(await screen.findByText("Qui passe ?")).toBeInTheDocument();
    expect(screen.getByText(/Priorité à droite/)).toBeInTheDocument();
    expect(screen.getByText("/ 1")).toBeInTheDocument();
    expect(screen.getByText("Incorrect")).toBeInTheDocument();
  });
});
```

- [ ] **Step 5: Write the history test — `frontend/src/app/history/page.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import HistoryPage from "./page";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

beforeEach(() => vi.spyOn(api, "getMe").mockResolvedValue({ id: 1, email: "a@b.com" }));
afterEach(() => vi.restoreAllMocks());

function renderHistory() {
  return render(
    <AuthProvider>
      <HistoryPage />
    </AuthProvider>,
  );
}

describe("HistoryPage", () => {
  it("lists completed attempts with a pass badge and a review link", async () => {
    vi.spyOn(api, "getHistory").mockResolvedValue([
      { id: 9, started_at: "2026-07-04T10:00:00Z", finished_at: "2026-07-04T10:10:00Z", score: 38, passed: true, status: "completed" },
    ]);
    renderHistory();
    expect(await screen.findByText(/Score 38 \/ 40/)).toBeInTheDocument();
    expect(screen.getByText("Réussi")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Revoir" })).toHaveAttribute(
      "href",
      "/exam/9/review",
    );
  });

  it("shows an empty state when there are no attempts", async () => {
    vi.spyOn(api, "getHistory").mockResolvedValue([]);
    renderHistory();
    expect(await screen.findByText(/Aucun examen/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 6: Verify (nvm first)**

Run: `npm test` (all pass), `npm run lint` (exit 0), `npm run build` (all routes compile: `/exam`, `/exam/[attemptId]/review`, `/history`).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/app/exam/ frontend/src/app/history/ frontend/src/components/exam/ReviewQuestionCard.tsx
git commit -m "feat(frontend): add exam review and history pages"
```

---

## Controller verification (live, after Task 4)

Not a subagent task — the controller runs the real backend + frontend and walks the full loop in a browser-equivalent way: log in → start exam → answer through the timed questions → land on the review with the score banner + corrections → open history and follow a "Revoir" link. Confirms the runner/timer/submit/review/history flow works end-to-end against the real API + placeholder question bank.

## Self-Review

**Spec coverage (spec §6 exam flow + §7 UI):**
- Timed runner, 20s/question, auto-advance, no going back → Task 3 + `useCountdown` (Task 2). ✓
- A–D multi-select with clear selected state → `OptionCard` (Task 2), runner toggle (Task 3). ✓
- Question media (image/video) → `QuestionMedia` (Task 2). ✓
- Progress indicator "X / Y" → `ProgressIndicator` (Task 2). ✓
- Server-side scoring already done in Phase 3; runner submits and shows result → Task 3 → review (Task 4). ✓
- Review screen: your selection, correct answer(s), explanation, media → `ReviewQuestionCard` (Task 4). ✓
- History list (date, score, pass/fail) linking to review → Task 4. ✓
- Dashboard links (`/exam`, `/history`) from Phase 4a now resolve. ✓

**Placeholder scan:** No TBDs; all component/page/test code complete. `next/image` deliberately not used (documented) to avoid remote-domain config; a scoped `eslint-disable` for `@next/next/no-img-element` keeps the lint gate green.

**Type consistency:** exam types defined once in `lib/api.ts` (Task 1), consumed by components (Task 2) and pages (Tasks 3–4). `useCountdown(seconds, onExpire) -> number` used by `Countdown` (Task 2) and reset via `key` in the runner (Task 3). `SubmittedAnswer` shape matches the backend submit contract. `mediaUrl` used by `QuestionMedia`.

**Lint discipline:** `useCountdown` avoids setState-in-effect (decrement inside `setTimeout`, reset via remount `key`) — no repeat of the Phase 4a lint error.

**Deferred to Phase 5:** polish (empty-scaffold README/asset cleanup), per-theme results breakdown (spec §11 nice-to-have), single-active-attempt policy decision, and populating the real question bank + media.
