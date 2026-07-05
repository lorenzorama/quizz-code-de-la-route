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
  const [submitFailed, setSubmitFailed] = useState(false);
  const [attemptId, setAttemptId] = useState<number | null>(null);
  const [questions, setQuestions] = useState<ExamQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const answersRef = useRef<SubmittedAnswer[]>([]);
  const startedAtRef = useRef<number>(0);
  const advancingRef = useRef(false);
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

  async function submitAnswers() {
    advancingRef.current = false;
    setSubmitFailed(false);
    setPhase("submitting");
    try {
      const result = await api.submitExam(attemptId as number, answersRef.current);
      router.push(`/exam/${result.attempt_id}/review`);
    } catch {
      setErrorMsg("Échec de l'envoi de l'examen.");
      setSubmitFailed(true);
      setPhase("error");
    }
  }

  async function advance() {
    if (advancingRef.current) return;
    advancingRef.current = true;

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
      advancingRef.current = false;
      return;
    }

    await submitAnswers();
  }

  if (phase === "loading") {
    return <Centered>Préparation de l&apos;examen…</Centered>;
  }
  if (phase === "error") {
    return (
      <Centered>
        <p className="text-slate-700">{errorMsg}</p>
        {submitFailed ? (
          <Button className="mt-4" onClick={submitAnswers}>
            Réessayer
          </Button>
        ) : (
          <Link href="/" className="mt-4 inline-block">
            <Button variant="secondary">Retour à l&apos;accueil</Button>
          </Link>
        )}
      </Centered>
    );
  }
  if (phase === "submitting") {
    return <Centered>Calcul de votre score…</Centered>;
  }

  const question = questions[index];
  const isLast = index + 1 === questions.length;
  const hasMedia = question.media_type !== "none" && Boolean(question.media_path);

  return (
    <main className="mx-auto flex min-h-0 w-full max-w-4xl flex-1 flex-col gap-3 px-4 py-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:gap-6">
        <div className="sm:flex-1">
          <ProgressIndicator current={index + 1} total={questions.length} />
        </div>
        <div className="sm:flex-1">
          <Countdown key={index} seconds={SECONDS_PER_QUESTION} onExpire={advance} />
        </div>
      </div>

      <Card className="flex min-h-0 flex-1 flex-col gap-4 overflow-hidden md:flex-row md:items-stretch">
        {hasMedia ? (
          <div className="flex min-h-0 shrink-0 items-center justify-center md:w-1/2">
            <QuestionMedia
              mediaType={question.media_type}
              mediaPath={question.media_path}
            />
          </div>
        ) : null}
        <div className="flex min-h-0 flex-1 flex-col gap-3">
          <span className="w-fit rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
            {question.theme}
          </span>
          <h1 className="text-lg font-semibold text-slate-900">{question.text}</h1>
          <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto">
            {question.options.map((opt) => (
              <OptionCard
                key={opt.id}
                option={opt}
                selected={selected.includes(opt.id)}
                onToggle={() => toggle(opt.id)}
              />
            ))}
          </div>
        </div>
      </Card>

      <div className="flex shrink-0 justify-end">
        <Button onClick={advance}>{isLast ? "Terminer" : "Suivant"}</Button>
      </div>
    </main>
  );
}

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col items-center justify-center px-4 text-center text-slate-600">
      {children}
    </div>
  );
}

export default function ExamPage() {
  return (
    <RequireAuth>
      <div className="flex h-dvh flex-col overflow-hidden">
        <TopBar />
        <Runner />
      </div>
    </RequireAuth>
  );
}
