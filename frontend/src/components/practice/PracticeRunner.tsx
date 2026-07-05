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
