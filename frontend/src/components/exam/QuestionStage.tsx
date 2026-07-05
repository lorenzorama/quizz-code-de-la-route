"use client";

import { OptionCard } from "@/components/exam/OptionCard";
import { QuestionMedia } from "@/components/exam/QuestionMedia";
import type { ExamOption } from "@/lib/api";

/**
 * Shared quiz layout used by both the practice and exam runners: the situation
 * photo on top (filling the remaining vertical space), then the theme badge,
 * the question, and the choices in a 1-column (mobile) / 2-column (desktop)
 * grid. Designed to live inside a `min-h-0 flex-1` flex column so the whole
 * thing fits the viewport without scrolling — the photo shrinks first while the
 * question and choices keep their natural height.
 */
export function QuestionStage({
  theme,
  text,
  mediaType,
  mediaPath,
  options,
  selectedIds,
  onToggle,
}: {
  theme: string;
  text: string;
  mediaType: string;
  mediaPath: string | null;
  options: ExamOption[];
  selectedIds: number[];
  onToggle: (optionId: number) => void;
}) {
  const hasMedia = mediaType !== "none" && Boolean(mediaPath);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      {hasMedia ? (
        <div className="flex min-h-0 flex-1 items-center justify-center">
          <QuestionMedia fill mediaType={mediaType} mediaPath={mediaPath} />
        </div>
      ) : null}
      <div className="flex shrink-0 flex-col gap-3">
        <span className="w-fit rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-indigo-700">
          {theme}
        </span>
        <h1 className="text-lg font-semibold text-slate-900">{text}</h1>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {options.map((opt) => (
            <OptionCard
              key={opt.id}
              option={opt}
              selected={selectedIds.includes(opt.id)}
              onToggle={() => onToggle(opt.id)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
