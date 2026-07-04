# Phase 4a — Frontend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up the Next.js frontend with a lightweight, modern indigo design system, a typed API client to the FastAPI backend, cookie-based auth (register/login/logout + current-user context), auth pages, and a protected dashboard shell — plus the backend CORS needed for the browser to call the API with credentials.

**Architecture:** A Next.js (App Router, TypeScript) app in `frontend/`, styled with Tailwind using its built-in `indigo`/`slate` palette directly (no custom theme config, so it is Tailwind-v3/v4-agnostic) and the Inter font. A small typed `lib/api.ts` fetch wrapper (always `credentials: "include"`) talks to the backend; `lib/auth.tsx` provides an `AuthProvider` + `useAuth()` hook that hydrates the current user from `GET /auth/me`. Reusable UI primitives (`Button`, `Input`, `Field`, `Card`) encode the design system as fixed class recipes. Logic (api client, auth context) is unit-tested with Vitest + React Testing Library (fetch mocked). The backend gains a CORS middleware allowing the frontend origin with credentials.

**Tech Stack:** Next.js (App Router) + React + TypeScript, Tailwind CSS (built-in palette), Inter via `next/font`, Vitest + @testing-library/react + jsdom. Backend: FastAPI CORS middleware.

## Global Constraints

- Frontend lives in `frontend/` at the repo root (sibling of `backend/`). Run frontend commands from `frontend/`.
- **Design system (indigo, light theme):** primary `indigo-600` (hover `indigo-700`), page background `slate-50`, surfaces `white`; headings `slate-900`, muted text `slate-600`; cards `rounded-xl border border-slate-200 bg-white shadow-sm`; inputs `rounded-lg border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500`; success `emerald-600`, error `red-600`; font **Inter**; generous spacing, responsive, accessible (labels, focus states, sufficient contrast). Use Tailwind's built-in `indigo`/`slate`/`emerald`/`red` scales directly in `className` — do NOT add a custom Tailwind theme config (keeps it version-agnostic).
- API base URL from `process.env.NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`). The API client ALWAYS sends `credentials: "include"` so the session cookie flows.
- The session cookie is `SameSite=Lax`; `localhost:3000` ↔ `localhost:8000` are same-site (same host), so the cookie is sent on these cross-port requests. No cookie changes needed.
- Backend CORS must use an explicit origin list (not `*`) with `allow_credentials=True` (required when credentials are included).
- Every task ends with its stated verification (a passing test run, a successful build, or both) and a commit.
- Do NOT run `create-next-app` inside an existing `frontend/` dir twice; if the dir exists from a prior attempt, report it.

---

### Task 1: Backend CORS support

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_cors.py`

**Interfaces:**
- Produces: `settings.cors_origins: list[str]` (default `["http://localhost:3000"]`); a `CORSMiddleware` on the app allowing those origins with credentials.

- [ ] **Step 1: Add the `cors_origins` setting to `app/config.py`**

Add this field to the `Settings` class (alongside the existing fields):

```python
    cors_origins: list[str] = ["http://localhost:3000"]
```

- [ ] **Step 2: Add the CORS middleware in `app/main.py`**

Add the import near the other FastAPI imports:

```python
from fastapi.middleware.cors import CORSMiddleware
```

And add this immediately after `app = FastAPI(title="Quizz Code de la Route API")` (before the router includes / media mount):

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Ensure `from app.config import settings` is present in `main.py` (it already is, used by the media mount).

- [ ] **Step 3: Write the failing test — `tests/test_cors.py`**

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_cors_allows_configured_origin_with_credentials():
    resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_cors_preflight_allows_post():
    resp = client.options(
        "/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert resp.status_code in (200, 204)
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:3000"
```

- [ ] **Step 4: Run the tests (from `backend/`, venv active)**

Run: `pytest tests/test_cors.py -v`
Expected: 2 tests PASS.

- [ ] **Step 5: Run the full backend suite**

Run: `pytest -q`
Expected: all pass (no regressions).

- [ ] **Step 6: Commit**

```bash
git add backend/app/config.py backend/app/main.py backend/tests/test_cors.py
git commit -m "feat(backend): enable CORS for the frontend origin with credentials"
```

---

### Task 2: Next.js scaffold, Inter font, design-system UI primitives, Vitest

**Files:**
- Create: `frontend/` (via `create-next-app`)
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/globals.css` (only if needed to remove scaffold default styles that fight the design)
- Create: `frontend/src/components/ui/Button.tsx`
- Create: `frontend/src/components/ui/Input.tsx`
- Create: `frontend/src/components/ui/Field.tsx`
- Create: `frontend/src/components/ui/Card.tsx`
- Create: `frontend/.env.example`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/vitest.setup.ts`
- Create: `frontend/src/components/ui/Button.test.tsx`
- Modify: `frontend/package.json` (add the `test` script)

**Interfaces:**
- Produces: `Button` (variants `primary`/`secondary`/`ghost`), `Input`, `Field` (label + error wrapper), `Card` components; Inter applied app-wide; `npm test` runs Vitest.

- [ ] **Step 1: Scaffold the Next.js app**

Run from the repo root:
```bash
npx --yes create-next-app@latest frontend --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --yes
```
Expected: creates `frontend/` with TypeScript, Tailwind, App Router, `src/` dir. (Accept whatever Tailwind major version it installs — we only use built-in palette classes, which work in both v3 and v4. If a flag is rejected by your installed create-next-app version, drop that flag and accept the interactive default that matches it, and note the deviation in your report.)

- [ ] **Step 2: Install test dependencies**

Run from `frontend/`:
```bash
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

- [ ] **Step 3: Create `frontend/vitest.config.ts`**

```typescript
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
```

- [ ] **Step 4: Create `frontend/vitest.setup.ts`**

```typescript
import "@testing-library/jest-dom";
```

- [ ] **Step 5: Add the `test` script to `frontend/package.json`**

In the `"scripts"` object, add:

```json
    "test": "vitest run",
    "test:watch": "vitest"
```

- [ ] **Step 6: Apply the Inter font in `frontend/src/app/layout.tsx`**

Replace the file with:

```tsx
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Quizz Code de la Route",
  description: "Entraînez-vous à l'examen du code de la route.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body className={`${inter.className} min-h-screen bg-slate-50 text-slate-900 antialiased`}>
        {children}
      </body>
    </html>
  );
}
```

- [ ] **Step 7: Ensure `globals.css` doesn't fight the design**

Open `frontend/src/app/globals.css`. Keep the Tailwind import/directives at the top (whatever the scaffold generated — e.g. `@import "tailwindcss";` for v4 or the three `@tailwind` directives for v3). REMOVE any scaffold-added `:root`/`body` color rules or dark-mode `@media (prefers-color-scheme: dark)` block that sets background/foreground colors, since the design is light-theme and colors come from the `layout.tsx` body classes. Leave only the Tailwind import(s) plus any `html { }` reset if present.

- [ ] **Step 8: Create `frontend/src/components/ui/Button.tsx`**

```tsx
import { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost";

const base =
  "inline-flex items-center justify-center rounded-lg px-4 py-2.5 text-sm font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none";

const variants: Record<Variant, string> = {
  primary: "bg-indigo-600 text-white hover:bg-indigo-700",
  secondary: "bg-white text-slate-900 border border-slate-300 hover:bg-slate-50",
  ghost: "bg-transparent text-indigo-700 hover:bg-indigo-50",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...props} />
  );
}
```

- [ ] **Step 9: Create `frontend/src/components/ui/Input.tsx`**

```tsx
import { InputHTMLAttributes } from "react";

export function Input({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`block w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${className}`}
      {...props}
    />
  );
}
```

- [ ] **Step 10: Create `frontend/src/components/ui/Field.tsx`**

```tsx
import { ReactNode } from "react";

export function Field({
  label,
  htmlFor,
  error,
  children,
}: {
  label: string;
  htmlFor: string;
  error?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={htmlFor} className="block text-sm font-medium text-slate-700">
        {label}
      </label>
      {children}
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
    </div>
  );
}
```

- [ ] **Step 11: Create `frontend/src/components/ui/Card.tsx`**

```tsx
import { HTMLAttributes } from "react";

export function Card({
  className = "",
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-xl border border-slate-200 bg-white p-6 shadow-sm ${className}`}
      {...props}
    />
  );
}
```

- [ ] **Step 12: Create `frontend/.env.example`**

```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 13: Write the component test — `frontend/src/components/ui/Button.test.tsx`**

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { Button } from "./Button";

describe("Button", () => {
  it("renders its label and fires onClick", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Commencer</Button>);
    const button = screen.getByRole("button", { name: "Commencer" });
    expect(button).toBeInTheDocument();
    await userEvent.click(button);
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("applies the primary variant styles by default", () => {
    render(<Button>Go</Button>);
    expect(screen.getByRole("button", { name: "Go" }).className).toContain(
      "bg-indigo-600",
    );
  });

  it("is not clickable when disabled", async () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Nope
      </Button>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Nope" }));
    expect(onClick).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 14: Run the component test**

Run (from `frontend/`): `npm test`
Expected: Button tests PASS.

- [ ] **Step 15: Verify the app builds**

Run (from `frontend/`): `npm run build`
Expected: build succeeds with no type errors.

- [ ] **Step 16: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): scaffold Next.js app with indigo design system and vitest"
```

---

### Task 3: Typed API client and auth context

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/lib/auth.tsx`
- Create: `frontend/src/lib/api.test.ts`
- Create: `frontend/src/lib/auth.test.tsx`

**Interfaces:**
- Consumes: nothing frontend-specific yet (backend endpoints `/auth/register|login|logout|me`).
- Produces:
  - `api.ts`: `type User = { id: number; email: string }`; `class ApiError extends Error { status: number }`; `register(email, password): Promise<User>`; `login(email, password): Promise<User>`; `logout(): Promise<void>`; `getMe(): Promise<User | null>` (returns `null` on 401). All use `credentials: "include"`.
  - `auth.tsx`: `AuthProvider` component; `useAuth(): { user: User | null; loading: boolean; login; register; logout; refresh }`.

- [ ] **Step 1: Create `frontend/src/lib/api.ts`**

```typescript
export type User = { id: number; email: string };

const BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : detail;
    } catch {
      // non-JSON error body; keep statusText
    }
    throw new ApiError(response.status, detail);
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function register(email: string, password: string): Promise<User> {
  return request<User>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string): Promise<User> {
  return request<User>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function logout(): Promise<void> {
  return request<void>("/auth/logout", { method: "POST" });
}

export async function getMe(): Promise<User | null> {
  try {
    return await request<User>("/auth/me");
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}
```

- [ ] **Step 2: Create `frontend/src/lib/auth.tsx`**

```tsx
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import * as api from "@/lib/api";
import type { User } from "@/lib/api";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    const me = await api.getMe();
    setUser(me);
  }, []);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const me = await api.login(email, password);
    setUser(me);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    await api.register(email, password);
    const me = await api.login(email, password);
    setUser(me);
  }, []);

  const logout = useCallback(async () => {
    await api.logout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, refresh }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
```

Note: `register` here auto-logs-in (calls login after register) so the UX is one step; this is a frontend convenience and does not change the backend contract (backend register still issues no session; the follow-up login does).

- [ ] **Step 3: Write the failing test — `frontend/src/lib/api.test.ts`**

```typescript
import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, getMe, login } from "./api";

function mockFetch(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: "",
    json: async () => body,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("login posts credentials and returns the user", async () => {
    const fetchMock = mockFetch(200, { id: 1, email: "a@b.com" });
    vi.stubGlobal("fetch", fetchMock);
    const user = await login("a@b.com", "password123");
    expect(user).toEqual({ id: 1, email: "a@b.com" });
    const [, options] = fetchMock.mock.calls[0];
    expect(options.credentials).toBe("include");
    expect(options.method).toBe("POST");
  });

  it("login throws ApiError with status on 401", async () => {
    vi.stubGlobal("fetch", mockFetch(401, { detail: "Invalid email or password" }));
    await expect(login("a@b.com", "wrong")).rejects.toMatchObject({
      status: 401,
      message: "Invalid email or password",
    });
    await expect(login("a@b.com", "wrong")).rejects.toBeInstanceOf(ApiError);
  });

  it("getMe returns null on 401 instead of throwing", async () => {
    vi.stubGlobal("fetch", mockFetch(401, { detail: "Not authenticated" }));
    expect(await getMe()).toBeNull();
  });

  it("getMe returns the user on 200", async () => {
    vi.stubGlobal("fetch", mockFetch(200, { id: 7, email: "c@d.com" }));
    expect(await getMe()).toEqual({ id: 7, email: "c@d.com" });
  });
});
```

- [ ] **Step 4: Write the failing test — `frontend/src/lib/auth.test.tsx`**

```tsx
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "./api";
import { AuthProvider, useAuth } from "./auth";

function Probe() {
  const { user, loading, login, logout } = useAuth();
  if (loading) return <p>loading</p>;
  return (
    <div>
      <p>user: {user ? user.email : "none"}</p>
      <button onClick={() => login("a@b.com", "password123")}>login</button>
      <button onClick={() => logout()}>logout</button>
    </div>
  );
}

afterEach(() => vi.restoreAllMocks());

describe("AuthProvider", () => {
  it("hydrates from getMe on mount (unauthenticated)", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText("user: none")).toBeInTheDocument());
  });

  it("login sets the user, logout clears it", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    vi.spyOn(api, "login").mockResolvedValue({ id: 1, email: "a@b.com" });
    vi.spyOn(api, "logout").mockResolvedValue();
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await waitFor(() => expect(screen.getByText("user: none")).toBeInTheDocument());
    await act(async () => {
      await userEvent.click(screen.getByRole("button", { name: "login" }));
    });
    await waitFor(() => expect(screen.getByText("user: a@b.com")).toBeInTheDocument());
    await act(async () => {
      await userEvent.click(screen.getByRole("button", { name: "logout" }));
    });
    await waitFor(() => expect(screen.getByText("user: none")).toBeInTheDocument());
  });
});
```

- [ ] **Step 5: Run the tests**

Run (from `frontend/`): `npm test`
Expected: all api + auth tests PASS (plus the Button test from Task 2).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/
git commit -m "feat(frontend): add typed API client and auth context"
```

---

### Task 4: Auth pages, provider wiring, and protected dashboard shell

**Files:**
- Modify: `frontend/src/app/layout.tsx` (wrap children in `AuthProvider`)
- Create: `frontend/src/components/AuthForm.tsx`
- Create: `frontend/src/app/login/page.tsx`
- Create: `frontend/src/app/register/page.tsx`
- Create: `frontend/src/app/page.tsx` (protected dashboard home)
- Create: `frontend/src/components/RequireAuth.tsx`
- Create: `frontend/src/components/TopBar.tsx`
- Create: `frontend/src/app/login/page.test.tsx`

**Interfaces:**
- Consumes: `useAuth` (Task 3), UI primitives (Task 2).
- Produces: `/login`, `/register`, `/` routes; `RequireAuth` guard (redirects to `/login` when unauthenticated); a `TopBar` with the user email + logout.

- [ ] **Step 1: Wrap the app in `AuthProvider` — edit `frontend/src/app/layout.tsx`**

Add the import and wrap `{children}`:

```tsx
import { AuthProvider } from "@/lib/auth";
```

Change the body to:

```tsx
      <body className={`${inter.className} min-h-screen bg-slate-50 text-slate-900 antialiased`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
```

- [ ] **Step 2: Create the shared `frontend/src/components/AuthForm.tsx`**

```tsx
"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { ApiError } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field } from "@/components/ui/Field";
import { Input } from "@/components/ui/Input";

export function AuthForm({
  title,
  submitLabel,
  onSubmit,
  footer,
}: {
  title: string;
  submitLabel: string;
  onSubmit: (email: string, password: string) => Promise<void>;
  footer: React.ReactNode;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit(email, password);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Une erreur est survenue.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4">
      <Card className="space-y-6">
        <div className="space-y-1">
          <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
          <p className="text-sm text-slate-600">Quizz Code de la Route</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          <Field label="Email" htmlFor="email">
            <Input
              id="email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>
          <Field label="Mot de passe" htmlFor="password">
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          {error ? (
            <p role="alert" className="text-sm text-red-600">
              {error}
            </p>
          ) : null}
          <Button type="submit" disabled={submitting} className="w-full">
            {submitting ? "…" : submitLabel}
          </Button>
        </form>
        <p className="text-center text-sm text-slate-600">{footer}</p>
      </Card>
    </main>
  );
}

export { Link };
```

- [ ] **Step 3: Create `frontend/src/app/login/page.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthForm } from "@/components/AuthForm";
import { useAuth } from "@/lib/auth";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();

  return (
    <AuthForm
      title="Connexion"
      submitLabel="Se connecter"
      onSubmit={async (email, password) => {
        await login(email, password);
        router.push("/");
      }}
      footer={
        <>
          Pas de compte ?{" "}
          <Link href="/register" className="font-semibold text-indigo-700 hover:underline">
            Créer un compte
          </Link>
        </>
      }
    />
  );
}
```

- [ ] **Step 4: Create `frontend/src/app/register/page.tsx`**

```tsx
"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { AuthForm } from "@/components/AuthForm";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { register } = useAuth();
  const router = useRouter();

  return (
    <AuthForm
      title="Créer un compte"
      submitLabel="S'inscrire"
      onSubmit={async (email, password) => {
        await register(email, password);
        router.push("/");
      }}
      footer={
        <>
          Déjà inscrit ?{" "}
          <Link href="/login" className="font-semibold text-indigo-700 hover:underline">
            Se connecter
          </Link>
        </>
      }
    />
  );
}
```

- [ ] **Step 5: Create the guard `frontend/src/components/RequireAuth.tsx`**

```tsx
"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <div className="flex min-h-screen items-center justify-center text-slate-500">
        Chargement…
      </div>
    );
  }
  return <>{children}</>;
}
```

- [ ] **Step 6: Create `frontend/src/components/TopBar.tsx`**

```tsx
"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/lib/auth";

export function TopBar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
        <span className="text-sm font-bold text-indigo-700">Code de la Route</span>
        <div className="flex items-center gap-3">
          {user ? <span className="text-sm text-slate-600">{user.email}</span> : null}
          <Button
            variant="secondary"
            onClick={async () => {
              await logout();
              router.replace("/login");
            }}
          >
            Déconnexion
          </Button>
        </div>
      </div>
    </header>
  );
}
```

- [ ] **Step 7: Create the protected dashboard `frontend/src/app/page.tsx`**

```tsx
"use client";

import Link from "next/link";
import { RequireAuth } from "@/components/RequireAuth";
import { TopBar } from "@/components/TopBar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export default function HomePage() {
  return (
    <RequireAuth>
      <TopBar />
      <main className="mx-auto max-w-4xl px-4 py-10">
        <div className="space-y-2">
          <h1 className="text-3xl font-bold text-slate-900">Bienvenue 👋</h1>
          <p className="text-slate-600">
            Prêt à vous entraîner à l&apos;examen du code de la route ?
          </p>
        </div>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          <Card className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold text-slate-900">Examen blanc</h2>
            <p className="text-sm text-slate-600">
              40 questions chronométrées, comme le vrai examen.
            </p>
            <Link href="/exam" className="mt-auto">
              <Button className="w-full">Commencer un examen</Button>
            </Link>
          </Card>
          <Card className="flex flex-col gap-3">
            <h2 className="text-lg font-semibold text-slate-900">Mon historique</h2>
            <p className="text-sm text-slate-600">
              Consultez vos scores et révisez vos erreurs.
            </p>
            <Link href="/history" className="mt-auto">
              <Button variant="secondary" className="w-full">
                Voir l&apos;historique
              </Button>
            </Link>
          </Card>
        </div>
      </main>
    </RequireAuth>
  );
}
```

Note: the `/exam` and `/history` links target routes built in Phase 4b; until then they 404, which is expected.

- [ ] **Step 8: Write the page test — `frontend/src/app/login/page.test.tsx`**

```tsx
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as api from "@/lib/api";
import { AuthProvider } from "@/lib/auth";
import LoginPage from "./page";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace: vi.fn() }) }));

afterEach(() => vi.restoreAllMocks());

function renderLogin() {
  return render(
    <AuthProvider>
      <LoginPage />
    </AuthProvider>,
  );
}

describe("LoginPage", () => {
  it("logs in and redirects home on success", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    vi.spyOn(api, "login").mockResolvedValue({ id: 1, email: "a@b.com" });
    renderLogin();
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "password123");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    await waitFor(() => expect(push).toHaveBeenCalledWith("/"));
  });

  it("shows an error message when login fails", async () => {
    vi.spyOn(api, "getMe").mockResolvedValue(null);
    vi.spyOn(api, "login").mockRejectedValue(
      new api.ApiError(401, "Invalid email or password"),
    );
    renderLogin();
    await userEvent.type(screen.getByLabelText("Email"), "a@b.com");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Se connecter" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Invalid email or password",
    );
  });
});
```

- [ ] **Step 9: Run the tests**

Run (from `frontend/`): `npm test`
Expected: all tests PASS (Button, api, auth, login page).

- [ ] **Step 10: Verify the app builds**

Run (from `frontend/`): `npm run build`
Expected: build succeeds, no type errors. (Routes `/`, `/login`, `/register` compile. `/exam` and `/history` don't exist yet — that's fine.)

- [ ] **Step 11: Commit**

```bash
git add frontend/
git commit -m "feat(frontend): add auth pages, route guard, and protected dashboard shell"
```

---

## Controller verification (live, after Task 4)

Not a subagent task — the controller runs the real backend + frontend and confirms the flow visually via the Preview tools: start Postgres/Redis + `uvicorn app.main:app`, run `frontend` dev server, then register → land on dashboard → logout → redirected to login. Confirms CORS + cookie auth work end-to-end in a browser (which unit tests with mocked fetch cannot).

## Self-Review

**Spec coverage (spec §7 UI/UX + §6 auth surface):**
- Lightweight modern indigo design system, Inter, responsive, accessible → Task 2 primitives + design-token constraints. ✓
- API client with credentialed cookie auth → Task 3. ✓
- Register/login/logout + current-user context → Task 3 (auth context) + Task 4 (pages). ✓
- Protected routes → Task 4 (`RequireAuth`). ✓
- Backend reachable from the browser (CORS + credentials) → Task 1. ✓

**Placeholder scan:** No TBDs; all component/logic/test code is complete. The `/exam` and `/history` links intentionally point at Phase 4b routes (documented).

**Type consistency:** `User = {id, email}` and `ApiError` defined in `api.ts` (Task 3), used by `auth.tsx` and tests. `useAuth()` shape (`user, loading, login, register, logout, refresh`) defined in Task 3, consumed in Task 4 pages/guard/topbar. UI primitives (`Button`/`Input`/`Field`/`Card`) defined Task 2, used Task 4. `settings.cors_origins` (Task 1) matches the frontend origin `http://localhost:3000`.

**Deferred to Phase 4b:** exam runner + 20s timer, results screen, review screen, history page (the `/exam` and `/history` routes), and their API client methods (`startExam`/`submitExam`/`getReview`/`getHistory`). Phase 5: polish + real content.
