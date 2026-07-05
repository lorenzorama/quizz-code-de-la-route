"use client";

import { useCountdown } from "@/lib/useCountdown";

export function Countdown({
  seconds,
  onExpire,
}: {
  seconds: number;
  onExpire: () => void;
}) {
  const remaining = useCountdown(seconds, onExpire);
  const pct = Math.max(0, Math.round((remaining / seconds) * 100));
  const low = remaining <= 5;

  return (
    <div className="space-y-1" aria-live="polite">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium text-slate-600">Temps restant</span>
        <span
          className={`font-semibold tabular-nums ${low ? "text-red-600" : "text-slate-900"}`}
        >
          {remaining}s
        </span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200">
        <div
          className={`h-full rounded-full transition-[width] duration-1000 ease-linear ${low ? "bg-red-500" : "bg-indigo-600"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
