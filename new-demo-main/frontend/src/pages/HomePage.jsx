import { useEffect, useState } from "react";

import ClaimItem from "../components/ClaimItem";
import InputForm from "../components/InputForm";
import ScoreBadge from "../components/ScoreBadge";
import SectionCard from "../components/SectionCard";

const confidenceStyles = {
  HIGH: "bg-emerald-500/12 text-emerald-300 ring-emerald-400/20",
  MEDIUM: "bg-amber-500/12 text-amber-300 ring-amber-400/20",
  LOW: "bg-slate-500/12 text-slate-300 ring-slate-400/20",
};

function getScoreColor(score) {
  if (score >= 75) return "#34d399";
  if (score >= 50) return "#fbbf24";
  return "#fb7185";
}

function TruthScorePanel({ report, productName }) {
  const score = report.truth_score;
  const radius = 56;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = getScoreColor(score);

  return (
    <SectionCard title="Truth Score">
      <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-white/[0.08] to-white/[0.03] p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-500">Current Product</p>
            <p className="mt-2 text-lg font-semibold text-slate-100">{productName || "Untitled product"}</p>
          </div>
          <ScoreBadge score={score} />
        </div>

        <div className="mt-5 flex items-center gap-5">
          <div className="relative flex h-36 w-36 items-center justify-center">
            <svg className="-rotate-90" width="144" height="144" viewBox="0 0 144 144">
              <circle cx="72" cy="72" r={radius} stroke="rgba(148,163,184,0.18)" strokeWidth="10" fill="none" />
              <circle
                cx="72"
                cy="72"
                r={radius}
                stroke={color}
                strokeWidth="10"
                strokeLinecap="round"
                fill="none"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
                style={{ transition: "stroke-dashoffset 700ms ease, stroke 300ms ease" }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-4xl font-semibold tracking-tight text-slate-50">{score}</span>
              <span className="text-xs uppercase tracking-[0.22em] text-slate-500">out of 100</span>
            </div>
          </div>

          <div className="min-w-0 flex-1 space-y-3">
            {Object.entries(report.dimensions).map(([label, value]) => (
              <div key={label}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs font-medium capitalize text-slate-300">{label}</span>
                  <span className="text-xs text-slate-500">{value}</span>
                </div>
                <div className="h-1.5 overflow-hidden rounded-full bg-white/8">
                  <div
                    className="h-full rounded-full bg-cyan-300 transition-all duration-700"
                    style={{ width: `${value}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </SectionCard>
  );
}

function LoadingState({ message }) {
  return (
    <SectionCard title="Analyzing">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-cyan-400/20 border-t-cyan-300" />
          <div>
            <p className="text-sm font-medium text-slate-100">{message}</p>
            <p className="text-xs text-slate-500">Building a grounded truth report.</p>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {["Detecting product", "Analyzing claims", "Evaluating trust"].map((step, index) => (
            <div
              key={step}
              className={`rounded-2xl border px-3 py-2 text-center text-[11px] font-medium uppercase tracking-[0.15em] ${
                message.startsWith(step)
                  ? "border-cyan-400/30 bg-cyan-400/10 text-cyan-200"
                  : index === 0 && message.startsWith("Analyzing")
                    ? "border-white/10 bg-white/[0.04] text-slate-400"
                    : "border-white/10 bg-white/[0.04] text-slate-500"
              }`}
            >
              {step}
            </div>
          ))}
        </div>
        <div className="space-y-2">
          <div className="h-14 animate-pulse rounded-2xl bg-white/6" />
          <div className="h-20 animate-pulse rounded-2xl bg-white/6" />
          <div className="h-16 animate-pulse rounded-2xl bg-white/6" />
        </div>
      </div>
    </SectionCard>
  );
}

function EmptyState() {
  return (
    <SectionCard title="No Report Yet">
      <div className="rounded-3xl border border-dashed border-white/10 bg-white/[0.03] px-4 py-8 text-center">
        <p className="text-sm font-medium text-slate-200">Insufficient data</p>
        <p className="mt-2 text-sm leading-6 text-slate-500">
          Add product copy and run an analysis to open the intelligence view.
        </p>
      </div>
    </SectionCard>
  );
}

function ErrorState({ message, onRetry }) {
  return (
    <SectionCard title="Error">
      <div className="rounded-3xl border border-rose-400/20 bg-rose-500/8 p-4">
        <p className="text-sm font-medium text-rose-100">Analysis unavailable</p>
        <p className="mt-2 text-sm leading-6 text-rose-200/90">{message}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-4 rounded-2xl border border-white/10 bg-white/6 px-4 py-2 text-sm font-medium text-white transition hover:border-rose-300/30 hover:bg-white/10"
        >
          Retry
        </button>
      </div>
    </SectionCard>
  );
}

function RealityInsights({ report }) {
  return (
    <SectionCard title="Reality Insights">
      {report.real_world.length ? (
        <div className="space-y-3">
          {report.real_world.map((item, index) => (
            <div
              key={`${item.feature}-${index}`}
              className="rounded-3xl border border-white/10 bg-white/[0.05] p-4 transition duration-200 hover:border-cyan-400/20 hover:bg-white/[0.07]"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <span className="mt-1 text-cyan-300">•</span>
                  <div>
                    <p className="text-sm font-semibold text-slate-100">{item.feature}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{item.insight}</p>
                  </div>
                </div>
                <span
                  className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.15em] ring-1 ring-inset ${
                    confidenceStyles[item.confidence]
                  }`}
                >
                  {item.confidence}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm leading-6 text-slate-500">Insufficient data for grounded real-world guidance.</p>
      )}
    </SectionCard>
  );
}

function VerdictCard({ verdict }) {
  return (
    <SectionCard title="Final Verdict">
      <div className="rounded-3xl border border-cyan-400/15 bg-gradient-to-br from-cyan-400/10 via-slate-900/70 to-violet-500/10 p-5 shadow-[0_0_0_1px_rgba(34,211,238,0.08),0_18px_50px_rgba(2,6,23,0.35)]">
        <p className="text-sm leading-7 text-slate-100">{verdict}</p>
      </div>
    </SectionCard>
  );
}

function ChatPanel({ disabled, messages, loading, error, onSubmit }) {
  const [draft, setDraft] = useState("");

  function handleSubmit(event) {
    event.preventDefault();
    if (!draft.trim()) return;
    onSubmit(draft);
    setDraft("");
  }

  useEffect(() => {
    if (disabled) {
      setDraft("");
    }
  }, [disabled]);

  return (
    <SectionCard title="Ask Follow-Up">
      <div className="space-y-4">
        <div className="max-h-60 space-y-3 overflow-y-auto rounded-3xl border border-white/10 bg-black/20 p-3">
          {!messages.length ? (
            <p className="text-sm leading-6 text-slate-500">
              Ask practical questions about the current report.
            </p>
          ) : (
            messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`max-w-[88%] rounded-2xl px-4 py-3 text-sm leading-6 transition ${
                  message.role === "user"
                    ? "ml-auto bg-cyan-400 text-slate-950"
                    : "bg-white/7 text-slate-200"
                }`}
              >
                {message.content}
              </div>
            ))
          )}
          {loading ? (
            <div className="max-w-[88%] rounded-2xl bg-white/7 px-4 py-3 text-sm text-slate-400">
              Analyzing...
            </div>
          ) : null}
        </div>

        {error ? (
          <div className="rounded-2xl border border-rose-400/20 bg-rose-500/8 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        ) : null}

        <form className="flex gap-2" onSubmit={handleSubmit}>
          <input
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            disabled={disabled || loading}
            placeholder="Ask about this product"
            className="min-w-0 flex-1 rounded-2xl border border-white/10 bg-white/6 px-4 py-3 text-sm text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-cyan-400/40 focus:ring-4 focus:ring-cyan-400/10 disabled:cursor-not-allowed disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={disabled || loading}
            className="rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 transition hover:shadow-[0_0_24px_rgba(34,211,238,0.3)] disabled:cursor-not-allowed disabled:bg-slate-500 disabled:text-slate-200"
          >
            Ask
          </button>
        </form>
      </div>
    </SectionCard>
  );
}

export default function HomePage({
  panelOpen,
  report,
  loading,
  loadingMessage,
  error,
  formData,
  onFormChange,
  onAnalyze,
  onTryExample,
  chatMessages,
  chatLoading,
  chatError,
  onChat,
}) {
  return (
    <main className="min-h-screen overflow-hidden bg-[#020617] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(34,211,238,0.14),_transparent_28%),radial-gradient(circle_at_bottom_left,_rgba(139,92,246,0.12),_transparent_30%)]" />

      <aside
        className={`fixed right-0 top-0 z-40 flex h-screen w-full max-w-[360px] transform flex-col border-l border-white/10 bg-slate-950/80 backdrop-blur-2xl transition-transform duration-300 ease-out ${
          panelOpen ? "translate-x-0" : "translate-x-[calc(100%-28px)]"
        }`}
      >
        <div className="flex items-center justify-between border-b border-white/10 px-5 py-4">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.24em] text-cyan-300">TruthCart</p>
            <p className="mt-1 text-xs text-slate-500">Intelligence panel</p>
          </div>
          {report ? <ScoreBadge score={report.truth_score} /> : null}
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
          <SectionCard title="Analyze Product">
            <InputForm
              formData={formData}
              onChange={onFormChange}
              onSubmit={onAnalyze}
              onTryExample={onTryExample}
              loading={loading}
            />
          </SectionCard>

          {error && !loading ? (
            <ErrorState message={error} onRetry={() => onAnalyze(formData)} />
          ) : null}

          {loading ? <LoadingState message={loadingMessage} /> : null}
          {!loading && !report && !error ? <EmptyState /> : null}

          {!loading && report ? (
            <>
              <TruthScorePanel report={report} productName={formData.product_name} />

              <SectionCard title="Flagged Claims">
                <div className="space-y-3">
                  {report.flagged_claims.length ? (
                    report.flagged_claims.map((claim, index) => (
                      <ClaimItem key={`${claim.claim}-${index}`} claim={claim} />
                    ))
                  ) : (
                    <p className="text-sm leading-6 text-slate-500">No major flagged claims.</p>
                  )}
                </div>
              </SectionCard>

              <RealityInsights report={report} />

              <VerdictCard verdict={report.verdict} />

              <SectionCard title="Signal Summary">
                <div className="space-y-2">
                  {report.tldr.map((item, index) => (
                    <div
                      key={`${item}-${index}`}
                      className="rounded-2xl border border-white/8 bg-white/[0.04] px-4 py-3 text-sm leading-6 text-slate-300"
                    >
                      {item}
                    </div>
                  ))}
                </div>
              </SectionCard>

              <ChatPanel
                disabled={!report}
                messages={chatMessages}
                loading={chatLoading}
                error={chatError}
                onSubmit={onChat}
              />
            </>
          ) : null}
        </div>
      </aside>
    </main>
  );
}
