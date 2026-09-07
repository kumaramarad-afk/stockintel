import Link from "next/link";
import { notFound } from "next/navigation";

import { apiGetSafe } from "@/lib/api";
import { formatChange, formatPrice } from "@/lib/format";
import type { ResearchNote, Stock } from "@/lib/types";

export default async function StockDetailPage({ params }: { params: { ticker: string } }) {
  const ticker = params.ticker.toUpperCase();
  const [stock, research] = await Promise.all([
    apiGetSafe<Stock | null>(`/api/v1/stocks/${ticker}`, null),
    apiGetSafe<ResearchNote[]>("/api/v1/research", []),
  ]);

  if (!stock) notFound();

  const change = formatChange(stock.latest_price?.change_percent);
  const related = research.filter((note) => note.ticker === stock.ticker);

  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-white/10 bg-ink-800/80 p-8 shadow-panel">
        <p className="text-sm text-slate-400">
          {stock.exchange} · {stock.sector} · {stock.industry}
        </p>
        <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
          <div>
            <h1 className="text-4xl font-semibold">{stock.ticker}</h1>
            <p className="mt-1 text-slate-300">{stock.name}</p>
          </div>
          <div className="text-right">
            <p className="text-3xl font-semibold">{formatPrice(stock.latest_price?.price)}</p>
            <p className={change.positive ? "text-emerald-400" : "text-rose-400"}>{change.label}</p>
          </div>
        </div>
        <p className="mt-6 max-w-3xl text-slate-300">{stock.description}</p>
      </section>

      <section>
        <h2 className="mb-4 text-xl font-semibold">Related research</h2>
        <div className="space-y-3">
          {related.map((note) => (
            <Link key={note.id} href={`/research/${note.id}`} className="block rounded-2xl border border-white/10 bg-ink-800/70 p-5 hover:bg-ink-700">
              <p className="font-medium">{note.title}</p>
              <p className="mt-1 text-sm text-slate-400">{note.summary}</p>
            </Link>
          ))}
          {related.length === 0 && <p className="text-sm text-slate-400">No notes tagged to this ticker yet.</p>}
        </div>
      </section>
    </div>
  );
}
