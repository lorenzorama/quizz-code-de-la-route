"use client";

import { ExamOption } from "@/lib/api";

export function OptionCard({
  option,
  selected,
  onToggle,
}: {
  option: ExamOption;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      aria-pressed={selected}
      className={`flex w-full items-center gap-3 rounded-xl border p-4 text-left transition-colors ${
        selected
          ? "border-indigo-600 bg-indigo-50 ring-1 ring-indigo-600"
          : "border-slate-200 bg-white hover:bg-slate-50"
      }`}
    >
      <span
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-sm font-bold ${
          selected ? "bg-indigo-600 text-white" : "bg-slate-100 text-slate-700"
        }`}
      >
        {option.label}
      </span>
      <span className="text-sm text-slate-900">{option.text}</span>
    </button>
  );
}
