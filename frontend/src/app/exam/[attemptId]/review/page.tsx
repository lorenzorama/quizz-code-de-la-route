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
