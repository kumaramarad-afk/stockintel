"use client";

import { useEffect, useState } from "react";

import { fetchMarketQuotes, formatTapePercent, formatTapePrice, INDEX_SYMBOLS, type MarketQuote } from "@/lib/markets";

function TapeItem({ quote }: { quote: MarketQuote }) {
  const up = (quote.change_percent ?? 0) >= 0;
  const tone = quote.change_percent == null ? "text-slate-400" : up ? "text-emerald-400" : "text-rose-400";
  return (
    <span className="inline-flex items-center gap-2 px-6 text-[11px] font-medium tracking-wide text-slate-300">
      <span className="text-slate-200">{quote.name}</span>
      <span className="font-mono text-slate-400">{formatTapePrice(quote.price)}</span>
      <span className={`font-mono ${tone}`}>{formatTapePercent(quote.change_percent)}</span>
    </span>
  );
}

const PLACEHOLDERS: MarketQuote[] = [
  { symbol: "^GSPC", name: "S&P 500", price: null, change_percent: null },
  { symbol: "^IXIC", name: "Nasdaq", price: null, change_percent: null },
  { symbol: "^DJI", name: "Dow Jones", price: null, change_percent: null },
];

export function MarketTicker() {
  const [quotes, setQuotes] = useState<MarketQuote[]>(PLACEHOLDERS);

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      void fetchMarketQuotes(INDEX_SYMBOLS)
        .then((rows) => {
          if (!cancelled && rows.length) setQuotes(rows);
        })
        .catch(() => undefined);
    };
    load();
    const timer = window.setInterval(load, 60_000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const loop = [...quotes, ...quotes, ...quotes, ...quotes];

  return (
    <div className="relative overflow-hidden border-b border-slate-800/60 bg-slate-950">
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-16 bg-gradient-to-r from-slate-950 to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-16 bg-gradient-to-l from-slate-950 to-transparent" />
      <div className="flex w-max animate-marquee py-1.5 hover:[animation-play-state:paused]">
        {loop.map((quote, index) => (
          <TapeItem key={`${quote.symbol}-${index}`} quote={quote} />
        ))}
      </div>
    </div>
  );
}
