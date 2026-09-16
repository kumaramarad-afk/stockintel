import Link from "next/link";

import { HomeSearch } from "@/components/research/HomeSearch";
import { apiGetSafe } from "@/lib/api";

type DirectoryResponse = {
  tickers: Array<{ ticker: string; one_line?: string | null }>;
};

const EXAMPLES = ["AAPL", "NVDA", "TSLA"] as const;

export const metadata = {
  title: "GetStockReport — Research that shows the reasoning, not a verdict",
  description: "Bull case, bear case, what has to be true — you decide. Browse 50+ research reports.",
};

export default async function HomePage() {
  const directory = await apiGetSafe<DirectoryResponse>("/api/v1/research/tickers", { tickers: [] });
  const byTicker = Object.fromEntries(directory.tickers.map((row) => [row.ticker, row.one_line]));
  const fallbacks: Record<string, string> = {
    AAPL: "Apple is trading near record highs on a multiple it has almost never sustained — while a material slice of earnings sits downstream of a contested partnership.",
    NVDA: "NVIDIA is priced for continued AI infrastructure dominance, against customer concentration and cyclical demand that the multiple already assumes will hold.",
    TSLA: "Tesla trades as both an auto company and an autonomy bet — the current price needs more than unit growth to justify the premium.",
  };

  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(16,185,129,0.18),_transparent_55%)]" />
      <div className="relative mx-auto flex min-h-[70vh] max-w-3xl flex-col justify-center gap-10 py-10">
        <div className="space-y-4 text-center">
          <p className="text-xs font-semibold tracking-[0.22em] text-emerald-400">GETSTOCKREPORT</p>
          <h1 className="text-4xl font-semibold tracking-tight text-slate-50 sm:text-5xl">
            Every stock research site ends with a score. We end with the reasoning.
          </h1>
          <p className="text-lg text-slate-400">Bull case, bear case, what has to be true — you decide.</p>
        </div>

        <HomeSearch />

        <div className="space-y-3">
          {EXAMPLES.map((ticker) => (
            <Link
              key={ticker}
              href={`/research/${ticker}`}
              className="block rounded-2xl border border-slate-800 bg-slate-900/60 px-5 py-4 text-left transition hover:border-emerald-500/40"
            >
              <p className="text-sm font-semibold text-emerald-400">{ticker}</p>
              <p className="mt-1 text-sm leading-6 text-slate-300">{byTicker[ticker] || fallbacks[ticker]}</p>
              <p className="mt-2 text-sm text-slate-500">Read full analysis →</p>
            </Link>
          ))}
        </div>

        <div className="text-center">
          <Link
            href="/research"
            className="inline-flex rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-400"
          >
            Browse all reports
          </Link>
        </div>
      </div>
    </section>
  );
}
