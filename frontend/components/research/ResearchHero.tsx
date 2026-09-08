"use client";

import { BarChart3, Lock, Search, Zap } from "lucide-react";
import { FormEvent, useEffect, useRef, useState } from "react";

import { fetchMarketQuotes, formatTapePercent, formatTapePrice, POPULAR_SYMBOLS, type MarketQuote } from "@/lib/markets";

const PILLARS = [
  { icon: Lock, label: "🔒 Gated Pro Signals" },
  { icon: Zap, label: "⚡ Instant AI Synthesis" },
  { icon: BarChart3, label: "📊 100% Verified Filings" },
] as const;

type ResearchHeroProps = {
  ticker: string;
  setTicker: (value: string) => void;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onSelect: (symbol: string) => void;
  showReport: boolean;
};

export function ResearchHero({ ticker, setTicker, onSubmit, onSelect, showReport }: ResearchHeroProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [quotes, setQuotes] = useState<MarketQuote[]>([]);
  const [isMac, setIsMac] = useState(false);

  useEffect(() => {
    setIsMac(/Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent));
    void fetchMarketQuotes(POPULAR_SYMBOLS)
      .then(setQuotes)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      const typing = target && (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable);
      if ((event.key === "/" && !typing) || ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k")) {
        event.preventDefault();
        inputRef.current?.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const quoteFor = (symbol: string) => quotes.find((item) => item.symbol.toUpperCase() === symbol);

  return (
    <div className={`relative overflow-hidden rounded-3xl px-4 text-center sm:px-8 ${showReport ? "py-8 sm:py-10" : "py-14 sm:py-20"}`}>
      <div className="pointer-events-none absolute left-1/2 top-0 h-[28rem] w-[28rem] -translate-x-1/2 rounded-full bg-emerald-500/10 blur-3xl" />
      <div className="hero-glow pointer-events-none absolute inset-0" />
      <div className="relative">
        <span className="inline-flex items-center rounded-full border border-slate-700/50 bg-slate-900/80 px-4 py-1.5 text-xs text-slate-300 shadow-inner">
          ⚡ Powered by Claude AI & Real-Time SEC EDGAR Data
        </span>
        <h1 className={`mt-5 font-semibold tracking-tight ${showReport ? "text-3xl sm:text-4xl" : "text-4xl sm:text-6xl"}`}>
          <span className="bg-gradient-to-r from-slate-100 via-slate-200 to-slate-400 bg-clip-text text-transparent">
            Institutional-Grade
          </span>{" "}
          <span className="text-slate-100">Stock Research.</span>
        </h1>
        {!showReport && (
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-slate-400 sm:text-base">
            Unfiltered fundamentals, options volatility, analyst consensus, and AI-driven deep dives for retail traders.
          </p>
        )}
        <form onSubmit={onSubmit} className="mx-auto mt-8 max-w-2xl">
          <label className="sr-only" htmlFor="ticker">
            Ticker symbol
          </label>
          <div className="flex items-center gap-2 rounded-2xl border border-slate-700/80 bg-slate-900/90 p-1.5 shadow-2xl transition focus-within:border-emerald-500 focus-within:ring-1 focus-within:ring-emerald-500">
            <Search className="ml-3 h-5 w-5 shrink-0 text-slate-500" aria-hidden="true" />
            <input
              ref={inputRef}
              id="ticker"
              value={ticker}
              onChange={(event) => setTicker(event.target.value.toUpperCase())}
              placeholder="Search a ticker — AAPL, NVDA, MSFT"
              autoComplete="off"
              spellCheck={false}
              className="min-w-0 flex-1 bg-transparent px-2 py-3 text-base font-medium tracking-[0.12em] text-slate-100 placeholder-slate-500 outline-none sm:text-lg"
            />
            <kbd className="hidden rounded-md border border-slate-700/70 bg-slate-950/80 px-2 py-1 font-mono text-[10px] text-slate-400 sm:inline">
              {isMac ? "⌘K" : "/"}
            </kbd>
            <button
              type="submit"
              disabled={ticker.trim().length === 0}
              className="rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 shadow-lg shadow-emerald-500/20 transition-all hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50 sm:px-6"
            >
              Analyze Stock
            </button>
          </div>
        </form>
        <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
          {POPULAR_SYMBOLS.map((symbol) => {
            const quote = quoteFor(symbol);
            const up = (quote?.change_percent ?? 0) >= 0;
            const tone = quote?.change_percent == null ? "text-slate-400" : up ? "text-emerald-400" : "text-rose-400";
            return (
              <button
                key={symbol}
                type="button"
                onClick={() => onSelect(symbol)}
                className="inline-flex items-center gap-2 rounded-full border border-slate-700/60 bg-slate-900/60 px-4 py-2 text-sm text-slate-200 shadow-inner backdrop-blur-md transition hover:border-emerald-500/40 hover:bg-slate-900"
              >
                <span className="font-semibold tracking-wide">{symbol}</span>
                <span className="font-mono text-xs text-slate-400">
                  {quote?.price != null ? `$${formatTapePrice(quote.price)}` : "—"}
                </span>
                <span className={`font-mono text-xs ${tone}`}>{formatTapePercent(quote?.change_percent)}</span>
              </button>
            );
          })}
        </div>
        <div className="mx-auto mt-10 grid max-w-3xl gap-3 sm:grid-cols-3">
          {PILLARS.map((pillar) => (
            <div
              key={pillar.label}
              className="flex items-center justify-center gap-2 rounded-2xl border border-slate-800/80 bg-slate-900/50 px-4 py-3 text-xs font-medium text-slate-300"
            >
              <pillar.icon className="h-4 w-4 text-emerald-400" aria-hidden="true" />
              {pillar.label}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
