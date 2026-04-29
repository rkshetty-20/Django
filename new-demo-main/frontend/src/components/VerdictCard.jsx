import SectionCard from "./SectionCard";

export default function VerdictCard({ verdict }) {
  return (
    <SectionCard title="Final Verdict">
      <div className="rounded-3xl border border-cyan-400/15 bg-gradient-to-br from-cyan-400/10 via-slate-900/70 to-violet-500/10 p-5 shadow-[0_0_0_1px_rgba(34,211,238,0.08),0_18px_50px_rgba(2,6,23,0.35)]">
        <p className="text-sm leading-7 text-slate-100">{verdict.summary}</p>
        <p className="mt-4 text-sm leading-6 text-slate-400">
          <span className="font-semibold text-slate-200">Best for:</span> {verdict.best_for}
        </p>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          <span className="font-semibold text-slate-200">Not ideal for:</span>{" "}
          {verdict.not_ideal_for}
        </p>
      </div>
    </SectionCard>
  );
}
