"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

type TickerRow = {
  ticker: string;
  name?: string | null;
  one_line?: string | null;
  price?: number | null;
};

export function ResearchDirectory({
  tickers,
  countLabel,
}: {
  tickers: TickerRow[];
  countLabel: string;
}) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const needle = query.trim().toUpperCase();
    if (!needle) return tickers;
    return tickers.filter(
      (row) =>
        row.ticker.includes(needle) ||
        (row.name || "").toUpperCase().includes(needle) ||
        (row.one_line || "").toUpperCase().includes(needle),
    );
  }, [query, tickers]);

  return (
    <section className="space-y-8">
      <div className="space-y-3">
        <p className="text-xs font-semibold tracking-[0.2em] text-emerald-400">RESEARCH</p>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-50">Research Reports</h1>
        <p className="max-w-2xl text-slate-400">
          Bull case, bear case, and what has to be true — no buy/sell verdict. {countLabel}.
        </p>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by ticker or company…"
          className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-100 outline-none ring-emerald-500/40 placeholder:text-slate-500 focus:ring"
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {filtered.map((row) => (
          <Link
            key={row.ticker}
            href={`/research/${encodeURIComponent(row.ticker)}`}
            className="rounded-2xl border border-slate-800 bg-slate-900/70 px-4 py-4 transition hover:border-emerald-500/40 hover:bg-slate-900"
          >
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-lg font-semibold text-slate-50">{row.ticker}</span>
              {row.name && <span className="truncate text-sm text-slate-500">{row.name}</span>}
            </div>
            {row.one_line ? (
              <p className="mt-2 line-clamp-2 text-sm leading-6 text-slate-400">{row.one_line}</p>
            ) : (
              <p className="mt-2 text-sm text-slate-500">Open research report →</p>
            )}
          </Link>
        ))}
      </div>
      {!filtered.length && <p className="text-slate-500">No tickers match that search.</p>}
    </section>
  );
}
