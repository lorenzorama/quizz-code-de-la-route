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
