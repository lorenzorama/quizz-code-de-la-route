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
