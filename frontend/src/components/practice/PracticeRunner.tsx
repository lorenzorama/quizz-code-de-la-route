"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { QuestionStage } from "@/components/exam/QuestionStage";
import { ReviewQuestionCard } from "@/components/exam/ReviewQuestionCard";
import { QuitToHome } from "@/components/QuitToHome";
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
      <main className="mx-auto flex min-h-0 w-full max-w-5xl flex-1 flex-col items-center justify-center gap-4 px-4 py-3 text-center text-slate-600">
        <p>Aucune question pour ces thèmes.</p>
        <Button variant="secondary" onClick={onFinish}>
          Retour
        </Button>
      </main>
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
    <main className="mx-auto flex min-h-0 w-full max-w-5xl flex-1 flex-col gap-3 px-4 py-3">
      <p className="shrink-0 text-sm font-medium text-slate-600">
        Question {index + 1} / {questions.length}
      </p>
      {revealed ? (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <ReviewQuestionCard question={reviewQuestion} index={index} />
        </div>
      ) : (
        <Card className="flex min-h-0 flex-1 flex-col overflow-hidden">
          <QuestionStage
            theme={question.theme}
            text={question.text}
            mediaType={question.media_type}
            mediaPath={question.media_path}
            options={question.options}
            selectedIds={selected}
            onToggle={toggle}
          />
        </Card>
      )}
      <div className="flex shrink-0 items-center justify-between">
        <QuitToHome message="Votre session d'entraînement sera interrompue." />
        {revealed ? (
          <Button onClick={next}>{isLast ? "Terminer" : "Suivant"}</Button>
        ) : (
          <Button
            onClick={() => setRevealed(true)}
            disabled={selected.length === 0}
          >
            Vérifier
          </Button>
        )}
      </div>
    </main>
  );
}
