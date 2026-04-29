export default function SectionCard({ title, children, className = "" }) {
  return (
    <section
      className={`rounded-3xl border border-white/10 bg-white/6 p-4 shadow-[0_10px_30px_rgba(2,6,23,0.22)] backdrop-blur-xl transition duration-200 hover:border-cyan-400/20 hover:bg-white/[0.08] ${className}`}
    >
      <h2 className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}
