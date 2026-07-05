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
