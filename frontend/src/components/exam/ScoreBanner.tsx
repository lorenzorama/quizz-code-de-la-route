export function ScoreBanner({
  score,
  total,
  passed,
}: {
  score: number;
  total: number;
  passed: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-6 text-center ${
        passed ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50"
      }`}
    >
      <p className="text-sm font-medium text-slate-600">Votre score</p>
      <p className="mt-1 text-4xl font-bold text-slate-900">
        {score}
        <span className="text-2xl text-slate-400"> / {total}</span>
      </p>
      <p
        className={`mt-2 text-lg font-semibold ${
          passed ? "text-emerald-700" : "text-red-700"
        }`}
      >
        {passed ? "Réussi ✅" : "Échoué ❌"}
      </p>
    </div>
  );
}
