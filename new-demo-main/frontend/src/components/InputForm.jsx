export default function InputForm({ formData, onChange, onSubmit, onTryExample, loading }) {
  function handleChange(event) {
    const { name, value } = event.target;
    onChange({
      ...formData,
      [name]: value,
    });
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (loading) return;
    onSubmit(formData);
  }

  return (
    <form className="space-y-4" onSubmit={handleSubmit}>
      <div>
        <label htmlFor="product_name" className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Product Name
        </label>
        <input
          id="product_name"
          name="product_name"
          value={formData.product_name}
          onChange={handleChange}
          placeholder="Example: Pixel 10 Pro"
          className="w-full rounded-2xl border border-white/10 bg-white/6 px-4 py-3 text-sm text-slate-100 outline-none transition duration-200 placeholder:text-slate-500 focus:border-cyan-400/40 focus:bg-white/[0.08] focus:ring-4 focus:ring-cyan-400/10"
          required
        />
      </div>

      <div>
        <label
          htmlFor="marketing_text"
          className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500"
        >
          Marketing Text
        </label>
        <textarea
          id="marketing_text"
          name="marketing_text"
          value={formData.marketing_text}
          onChange={handleChange}
          rows={8}
          placeholder="Paste product page copy, ad claims, launch highlights, and comparison lines."
          className="w-full rounded-2xl border border-white/10 bg-white/6 px-4 py-3 text-sm text-slate-100 outline-none transition duration-200 placeholder:text-slate-500 focus:border-cyan-400/40 focus:bg-white/[0.08] focus:ring-4 focus:ring-cyan-400/10"
          required
        />
      </div>

      <div>
        <label htmlFor="specs" className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
          Specs (Optional)
        </label>
        <textarea
          id="specs"
          name="specs"
          value={formData.specs}
          onChange={handleChange}
          rows={6}
          placeholder="Paste specs as JSON or plain text."
          className="w-full rounded-2xl border border-white/10 bg-white/6 px-4 py-3 text-sm text-slate-100 outline-none transition duration-200 placeholder:text-slate-500 focus:border-cyan-400/40 focus:bg-white/[0.08] focus:ring-4 focus:ring-cyan-400/10"
        />
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="submit"
          disabled={loading}
          className="inline-flex items-center rounded-2xl bg-gradient-to-r from-cyan-300 via-sky-400 to-violet-400 px-5 py-3 text-sm font-semibold text-slate-950 shadow-[0_0_0_1px_rgba(125,211,252,0.15),0_0_28px_rgba(34,211,238,0.24)] transition duration-200 hover:scale-[1.01] hover:shadow-[0_0_0_1px_rgba(125,211,252,0.25),0_0_34px_rgba(34,211,238,0.34)] disabled:cursor-not-allowed disabled:bg-slate-500 disabled:text-slate-200"
        >
          {loading ? (
            <>
              <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-slate-950/25 border-t-slate-950" />
              Analyzing…
            </>
          ) : (
            "Run Truth Analysis"
          )}
        </button>
        <button
          type="button"
          onClick={onTryExample}
          disabled={loading}
          className="inline-flex items-center rounded-2xl border border-white/10 bg-white/6 px-5 py-3 text-sm font-semibold text-slate-200 transition duration-200 hover:border-cyan-400/25 hover:bg-white/[0.08] disabled:cursor-not-allowed disabled:opacity-60"
        >
          Try Example
        </button>
      </div>
    </form>
  );
}
