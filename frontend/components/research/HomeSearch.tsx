"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export function HomeSearch() {
  const router = useRouter();
  const [ticker, setTicker] = useState("");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const symbol = ticker.trim().toUpperCase();
    if (!symbol) return;
    router.push(`/research/${encodeURIComponent(symbol)}`);
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
      <input
        value={ticker}
        onChange={(event) => setTicker(event.target.value)}
        placeholder="Search any ticker (AAPL, NVDA…)"
        className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-100 outline-none ring-emerald-500/40 placeholder:text-slate-500 focus:ring"
      />
      <button type="submit" className="rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-400">
        Open report
      </button>
    </form>
  );
}
