"use client";

import Link from "next/link";
import { useCallback, useMemo, useState } from "react";

import { SearchBox, type SearchHit } from "@/components/SearchBox";

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
  const [queryActive, setQueryActive] = useState(false);
  const [hits, setHits] = useState<SearchHit[]>([]);

  const onResultsChange = useCallback((rows: SearchHit[]) => {
    setHits(rows);
    setQueryActive(true);
  }, []);

  const visible = useMemo(() => {
    if (!queryActive || hits.length === 0) {
      // When search returned nothing for a query, show empty; when idle, show all SSR tickers.
      if (queryActive && hits.length === 0) return [];
      return tickers;
    }
    const byTicker = Object.fromEntries(tickers.map((row) => [row.ticker, row]));
    return hits.map((hit) => {
      const existing = byTicker[hit.ticker];
      return {
        ticker: hit.ticker,
        name: hit.company_name || hit.name || existing?.name,
        one_line: existing?.one_line,
        price: existing?.price,
      } satisfies TickerRow;
    });
  }, [hits, queryActive, tickers]);

  return (
    <section className="space-y-8">
      <div className="space-y-3">
        <p className="text-xs font-semibold tracking-[0.2em] text-emerald-400">RESEARCH</p>
        <h1 className="text-4xl font-semibold tracking-tight text-slate-50">Research Reports</h1>
        <p className="max-w-2xl text-slate-400">
          Bull case, bear case, and what has to be true — no buy/sell verdict. {countLabel}.
        </p>
        <SearchBox
          showButton={false}
          loadAllWhenEmpty
          debounceMs={300}
          placeholder="Search any US stock — ticker or company…"
          onResultsChange={onResultsChange}
          className="max-w-md"
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {visible.map((row) => (
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
              <p className="mt-2 text-sm text-slate-500">
                {row.name ? `${row.ticker} — ${row.name}` : "Open research report →"}
              </p>
            )}
          </Link>
        ))}
      </div>
      {!visible.length && <p className="text-slate-500">No results</p>}
    </section>
  );
}
