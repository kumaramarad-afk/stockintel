"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { ResearchHero } from "@/components/research/ResearchHero";
import { useAuth } from "@/components/layout/AuthProvider";
import { apiUrl } from "@/lib/api";
import { hasNewsletter, isPaidPlan } from "@/lib/plans";

/** Search entry that routes to public /research/[TICKER] pages. */
export function ResearchAnalyzer() {
  const router = useRouter();
  const { user, loading: authLoading, startCheckout } = useAuth();
  const [ticker, setTicker] = useState("");

  const load = useCallback(
    (symbol: string) => {
      sessionStorage.setItem("gsr_resume_ticker", symbol);
      router.push(`/research/${encodeURIComponent(symbol)}`);
    },
    [router],
  );

  useEffect(() => {
    if (authLoading) return;
    const fromQuery =
      typeof window === "undefined" ? "" : new URLSearchParams(window.location.search).get("ticker")?.trim().toUpperCase();
    if (fromQuery) {
      setTicker(fromQuery);
      load(fromQuery);
      return;
    }
  }, [authLoading, load]);

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const raw = ticker.trim();
    if (!raw) return;
    void (async () => {
      try {
        const response = await fetch(apiUrl(`/api/v1/research/resolve?q=${encodeURIComponent(raw)}`), {
          cache: "no-store",
        });
        if (response.ok) {
          const payload = (await response.json()) as { ticker?: string };
          if (payload.ticker) {
            load(payload.ticker);
            return;
          }
        }
      } catch {
        // Fall through to raw symbol.
      }
      load(raw.toUpperCase());
    })();
  }

  const remaining = Math.max(0, user?.reports_remaining ?? 5);
  const quotaExhausted = Boolean(user && !isPaidPlan(user.plan) && remaining <= 0);
  const quotaLabel =
    user && !isPaidPlan(user.plan) ? `${remaining} / ${user.reports_limit ?? 5} free reports remaining this month` : null;

  return (
    <section className="space-y-8">
      <ResearchHero
        ticker={ticker}
        setTicker={setTicker}
        onSubmit={onSubmit}
        showReport={false}
        quotaLabel={quotaLabel}
        quotaExhausted={quotaExhausted}
        onUpgrade={() => {
          void startCheckout();
        }}
        onSelect={(symbol) => {
          setTicker(symbol);
          load(symbol);
        }}
      />
      {!hasNewsletter(user?.plan) && (
        <div className="flex flex-col gap-3 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-50 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-semibold">Daily market briefing at 8 AM UTC</p>
            <p className="text-amber-100/80">Premium adds the morning desk and a 90-day archive for $12/month.</p>
          </div>
          <Link href="/newsletter" className="rounded-xl bg-emerald-500 px-4 py-2 text-center text-sm font-semibold text-slate-950 hover:bg-emerald-400">
            Open newsletter
          </Link>
        </div>
      )}
      <div className="text-center">
        <Link href="/research" className="text-sm text-emerald-400 hover:text-emerald-300">
          Or browse all reports →
        </Link>
      </div>
    </section>
  );
}
