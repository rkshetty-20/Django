export default function ReportSection({ items, emptyMessage, renderItem }) {
  if (!items?.length) {
    return <p className="text-sm text-slate-500">{emptyMessage}</p>;
  }

  return <div className="space-y-3">{items.map(renderItem)}</div>;
}
