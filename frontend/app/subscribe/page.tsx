"use client";

import Link from "next/link";
import { useState } from "react";

import { useAuth } from "@/components/layout/AuthProvider";
import { hasNewsletter, isPaidPlan } from "@/lib/plans";

export default function SubscribePage() {
  const { user, startCheckout, startBillingPortal, openAuthModal } = useAuth();
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubscribe(plan: "pro" | "newsletter_pro") {
    if (!user) {
      openAuthModal();
      return;
    }
    setBusy(true);
    setStatus(null);
    try {
      await startCheckout(plan);
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
        <h1 className="mt-3 text-4xl font-semibold">Choose your desk</h1>
        <p className="mt-3 text-gsr-muted">Five free reports each month. Pro unlocks every metric. Newsletter Pro adds the 8 AM briefing.</p>
      </div>
      <div className="mx-auto mt-10 grid max-w-5xl gap-6 lg:grid-cols-3">
        <article className="glass-card rounded-2xl p-6">
          <h2 className="text-xl font-semibold">Free registered</h2>
          <p className="mt-1 text-3xl font-semibold">$0</p>
          <ul className="mt-4 space-y-2 text-sm text-gsr-muted">
            <li>5 full reports per month</li>
            <li>Public preview after the monthly quota</li>
            <li>Consensus labels, not recommendations</li>
          </ul>
          <Link href="/" className="mt-6 inline-flex rounded-xl border border-gsr-border px-5 py-2.5 text-sm hover:border-gsr-accent">
            Start analyzing
          </Link>
        </article>
        <article className="glass-card rounded-2xl p-6">
          <h2 className="text-xl font-semibold">Pro</h2>
          <p className="mt-1 text-3xl font-semibold">
            $7 <span className="text-base font-normal text-gsr-muted">/ month</span>
          </p>
          <ul className="mt-4 space-y-2 text-sm text-gsr-muted">
            <li>Unlimited unredacted research</li>
            <li>Insider and institutional logs</li>
            <li>Coverage and filing alerts</li>
          </ul>
          {isPaidPlan(user?.plan) ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => void onCancel()}
              className="mt-6 rounded-xl border border-rose-400/40 px-5 py-2.5 text-sm font-semibold text-rose-200 hover:border-rose-300 disabled:opacity-60"
            >
              {busy ? "Opening…" : "Manage Subscription"}
            </button>
          ) : (
            <button
              type="button"
              disabled={busy}
              onClick={() => void onSubscribe("pro")}
              className="mt-6 rounded-xl bg-gsr-accent px-5 py-2.5 text-sm font-semibold text-gsr-bg hover:brightness-110 disabled:opacity-60"
            >
              Unlock Full Analyst Briefing ($7/mo)
            </button>
          )}
        </article>
        <article className="glass-card rounded-2xl border-gsr-accent/40 p-6 shadow-glass">
          <h2 className="text-xl font-semibold">Newsletter Pro</h2>
          <p className="mt-1 text-3xl font-semibold">
            $15 <span className="text-base font-normal text-gsr-muted">/ month</span>
          </p>
          <ul className="mt-4 space-y-2 text-sm text-gsr-muted">
            <li>Everything in Pro, unlimited</li>
            <li>Daily 8 AM UTC market briefing</li>
            <li>Deep-dive ticker linked to Research</li>
            <li>90-day searchable archive</li>
          </ul>
          {hasNewsletter(user?.plan) ? (
            <Link href="/newsletter" className="mt-6 inline-flex rounded-xl border border-gsr-border px-5 py-2.5 text-sm hover:border-gsr-accent">
              Open newsletter desk
            </Link>
          ) : (
            <button
              type="button"
              disabled={busy}
              onClick={() => void onSubscribe("newsletter_pro")}
              className="mt-6 rounded-xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:opacity-60"
            >
              Upgrade to Newsletter Pro ($15/mo)
            </button>
          )}
        </article>
      </div>
      {status && <p className="mx-auto mt-6 max-w-5xl text-sm text-gsr-muted">{status}</p>}
    </div>
  );
}
