"use client";

import Link from "next/link";
import { useState } from "react";

import { useAuth } from "@/components/layout/AuthProvider";
import { isPaidPlan } from "@/lib/plans";

export default function SubscribePage() {
  const { user, startCheckout, startBillingPortal, openAuthModal } = useAuth();
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubscribe() {
    if (!user) {
      openAuthModal();
      return;
    }
    setBusy(true);
    setStatus(null);
    try {
      await startCheckout();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not start checkout");
    } finally {
      setBusy(false);
    }
  }

  async function onCancel() {
    if (!user) {
      openAuthModal();
      return;
    }
    setBusy(true);
    setStatus(null);
    try {
      await startBillingPortal();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not open billing portal");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="py-8">
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gsr-accent">Subscribe</p>
        <h1 className="mt-3 text-4xl font-semibold">One Premium desk</h1>
        <p className="mt-3 text-gsr-muted">
          Five free reports each month. Premium is $12/month for unlimited research, the weekday briefing, and the archive.
        </p>
      </div>
      <div className="mx-auto mt-10 grid max-w-4xl gap-6 lg:grid-cols-2">
        <article className="glass-card rounded-2xl p-6">
          <h2 className="text-xl font-semibold">Free registered</h2>
          <p className="mt-1 text-3xl font-semibold">$0</p>
          <ul className="mt-4 space-y-2 text-sm text-gsr-muted">
            <li>Search and public previews</li>
            <li>5 full reports per month</li>
            <li>Guest preview after the monthly quota</li>
            <li>Consensus labels, not recommendations</li>
          </ul>
          <Link href="/" className="mt-6 inline-flex rounded-xl border border-gsr-border px-5 py-2.5 text-sm hover:border-gsr-accent">
            Start analyzing
          </Link>
        </article>
        <article className="glass-card rounded-2xl border-gsr-accent/40 p-6 shadow-glass">
          <h2 className="text-xl font-semibold">Premium</h2>
          <p className="mt-1 text-3xl font-semibold">
            $12 <span className="text-base font-normal text-gsr-muted">/ month</span>
          </p>
          <ul className="mt-4 space-y-2 text-sm text-gsr-muted">
            <li>Unlimited unredacted research</li>
            <li>Daily 8 AM UTC market briefing (Mon–Fri)</li>
            <li>90-day searchable archive</li>
            <li>Insider Form 4 and institutional logs</li>
            <li>Coverage and filing alerts</li>
          </ul>
          {isPaidPlan(user?.plan) ? (
            user?.complimentary ? (
              <Link href="/newsletter" className="mt-6 inline-flex rounded-xl border border-gsr-border px-5 py-2.5 text-sm hover:border-gsr-accent">
                Complimentary Premium is active
              </Link>
            ) : (
              <button
                type="button"
                disabled={busy}
                onClick={() => void onCancel()}
                className="mt-6 rounded-xl border border-rose-400/40 px-5 py-2.5 text-sm font-semibold text-rose-200 hover:border-rose-300 disabled:opacity-60"
              >
                {busy ? "Opening…" : "Manage Subscription"}
              </button>
            )
          ) : (
            <button
              type="button"
              disabled={busy}
              onClick={() => void onSubscribe()}
              className="mt-6 rounded-xl bg-gsr-accent px-5 py-2.5 text-sm font-semibold text-gsr-bg hover:brightness-110 disabled:opacity-60"
            >
              Unlock Premium ($12/mo)
            </button>
          )}
          <p className="mt-4 text-xs text-gsr-muted">
            Educational only. Not financial advice.{" "}
            <Link href="/legal/newsletter-disclaimer" className="text-gsr-accent hover:underline">
              Newsletter disclaimer
            </Link>
          </p>
        </article>
      </div>
      {status && <p className="mx-auto mt-6 max-w-4xl text-sm text-gsr-muted">{status}</p>}
    </div>
  );
}
