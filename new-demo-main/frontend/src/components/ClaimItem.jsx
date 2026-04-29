const classificationStyles = {
  VERIFIED: "bg-emerald-500/12 text-emerald-300 ring-emerald-400/20",
  CONDITIONAL: "bg-amber-500/12 text-amber-300 ring-amber-400/20",
  MISLEADING: "bg-rose-500/12 text-rose-300 ring-rose-400/20",
  "NON-VERIFIABLE": "bg-slate-500/12 text-slate-300 ring-slate-400/20",
};

const severityStyles = {
  HIGH: "bg-rose-400",
  MEDIUM: "bg-amber-400",
  LOW: "bg-slate-400",
};

export default function ClaimItem({ claim }) {
  return (
    <article className="rounded-3xl border border-white/10 bg-white/5 p-4 shadow-[0_8px_24px_rgba(2,6,23,0.2)] transition duration-200 hover:border-cyan-400/20 hover:bg-white/[0.07]">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`h-2.5 w-2.5 rounded-full ${severityStyles[claim.severity]}`} />
        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ring-inset ${
            classificationStyles[claim.classification] || classificationStyles["NON-VERIFIABLE"]
          }`}
        >
          {claim.classification}
        </span>
        <span className="text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500">
          {claim.severity}
        </span>
      </div>

      <p className="mt-4 text-sm font-medium leading-6 text-slate-100">"{claim.claim}"</p>
      <p className="mt-3 text-sm leading-6 text-slate-400">
        <span className="font-semibold text-slate-200">Reason:</span> {claim.reason}
      </p>
      <p className="mt-2 text-sm leading-6 text-slate-400">
        <span className="font-semibold text-slate-200">Reality:</span>{" "}
        {claim.realistic_interpretation}
      </p>
    </article>
  );
}
