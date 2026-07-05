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

  // Answering screen: fixed to the viewport, no page scroll.
  if (questions !== null) {
    return (
      <div className="flex h-dvh flex-col overflow-hidden">
        <TopBar />
        <PracticeRunner
          questions={questions}
          onFinish={() => {
            setQuestions(null);
            setSelected(new Set());
          }}
        />
      </div>
    );
  }

  // Theme selection / error / loading: normal scrollable page.
  return (
    <div className="flex min-h-dvh flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-2xl flex-1 space-y-4 px-4 py-8">
        {error ? (
          <p className="py-10 text-center text-slate-600">{error}</p>
        ) : !themes ? (
          <p className="py-10 text-center text-slate-500">Chargement…</p>
        ) : (
          <>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">
                Mode entraînement
              </h1>
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
                    aria-busy={loadingQuestions}
                  >
                    {loadingQuestions ? "…" : "Commencer"}
                  </Button>
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default function PracticePage() {
  return (
    <RequireAuth>
      <PracticeView />
    </RequireAuth>
  );
}
