function getScoreTone(score) {
  if (score >= 75) return "text-emerald-300";
  if (score >= 50) return "text-amber-300";
  return "text-rose-300";
}

export default function ScoreBadge({ score }) {
  return (
    <div className="inline-flex items-center rounded-full border border-white/10 bg-white/6 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
      <span>Truth Score</span>
      <span className={`ml-3 text-sm tracking-normal ${getScoreTone(score)}`}>{score}/100</span>
    </div>
  );
}
