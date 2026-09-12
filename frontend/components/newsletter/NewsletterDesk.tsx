"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { SubscribeForm } from "@/components/newsletter/SubscribeForm";
import { useAuth } from "@/components/layout/AuthProvider";
import { apiUrl } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { hasNewsletter, researchHref } from "@/lib/plans";
import type { NewsletterArchiveItem, NewsletterIssue, NewsletterStatus, NewsletterToday } from "@/lib/types";

type Props = {
  weeklyName: string;
  weeklyDescription: string;
  weeklySlug: string;
  issues: NewsletterIssue[];
};

export function NewsletterDesk({ weeklyName, weeklyDescription, weeklySlug, issues }: Props) {
  const { token, user, loading, openAuthModal, startCheckout, startBillingPortal } = useAuth();
  const [today, setToday] = useState<NewsletterToday | null>(null);
  const [status, setStatus] = useState<NewsletterStatus | null>(null);
  const [archive, setArchive] = useState<NewsletterArchiveItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const subscribed = hasNewsletter(user?.plan);

  useEffect(() => {
    const headers = token ? { Authorization: `Bearer ${token}` } : undefined;
    void fetch(apiUrl("/api/v1/newsletter/today"), { cache: "no-store", headers })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => setToday(payload))
      .catch(() => setToday(null));
  }, [token, user?.plan]);

  useEffect(() => {
    if (!token || !subscribed) {
      setStatus(null);
      setArchive([]);
      return;
    }
    const headers = { Authorization: `Bearer ${token}` };
    void fetch(apiUrl("/api/v1/newsletter/status"), { cache: "no-store", headers })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => setStatus(payload))
      .catch(() => setStatus(null));
    void fetch(apiUrl("/api/v1/newsletter/archive?page=1&limit=30"), { cache: "no-store", headers })
      .then((response) => (response.ok ? response.json() : []))
      .then((payload) => setArchive(Array.isArray(payload) ? payload : []))
      .catch(() => setArchive([]));
  }, [token, subscribed]);

  async function onUpgrade() {
    if (!user) {
      openAuthModal();
      return;
    }
    setBusy(true);
    setMessage(null);
    try {
      await startCheckout("newsletter_pro");
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not start checkout");
      setBusy(false);
    }
  }

  async function onToggleEmail() {
    if (!token) return;
    const next = status?.email_preference === "daily" ? "off" : "daily";
    setBusy(true);
    try {
      const response = await fetch(apiUrl("/api/v1/newsletter/email-preference"), {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ preference: next }),
      });
      if (!response.ok) throw new Error("Could not update email preference");
      setStatus((current) =>
        current
          ? { ...current, email_preference: next, newsletter_enabled: next === "daily" }
          : current,
      );
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Could not update preference");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="glass-card rounded-2xl p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gsr-accent">Newsletter Pro</p>
        <h1 className="mt-3 text-3xl font-semibold">Morning intelligence, then the full research desk</h1>
        <p className="mt-2 max-w-3xl text-gsr-muted">
          Daily briefing at 8 AM UTC with tape movers, the week’s earnings calendar, a macro watch, and one deep-dive
          ticker that opens the same institutional report on Research.
        </p>
        {!subscribed ? (
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <button
              type="button"
              disabled={busy || loading}
              onClick={() => void onUpgrade()}
              className="rounded-xl bg-gsr-accent px-5 py-3 text-sm font-semibold text-gsr-bg hover:brightness-110 disabled:opacity-60"
            >
              {busy ? "Redirecting…" : "Upgrade to Newsletter Pro — $15/mo"}
            </button>
            <p className="text-sm text-gsr-muted">Unlimited research included. Cancel anytime.</p>
          </div>
        ) : (
          <div className="mt-6 rounded-2xl border border-gsr-border bg-black/20 p-4 text-sm">
            <p className="font-semibold text-gsr-accent">Newsletter Pro is active</p>
            <p className="mt-1 text-gsr-muted">
              {status?.email_preference === "off"
                ? "Archive and unlimited research stay on. Daily email is paused."
                : "Daily emails are on for 8 AM UTC, Monday–Friday."}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy}
                onClick={() => void onToggleEmail()}
                className="rounded-xl border border-gsr-border px-4 py-2 hover:border-gsr-accent disabled:opacity-60"
              >
                {status?.email_preference === "off" ? "Resume daily email" : "Pause daily email"}
              </button>
              <button
                type="button"
                disabled={busy}
                onClick={() => void startBillingPortal().catch((err) => setMessage(err instanceof Error ? err.message : "Could not open billing"))}
                className="rounded-xl border border-gsr-border px-4 py-2 hover:border-gsr-accent disabled:opacity-60"
              >
                Manage billing
              </button>
            </div>
          </div>
        )}
        {message && <p className="mt-3 text-sm text-rose-300">{message}</p>}
      </section>

      <section className="glass-card rounded-2xl p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-gsr-muted">Today’s deep dive</p>
            <h2 className="mt-2 text-2xl font-semibold">{today?.ticker ?? "No pick published yet"}</h2>
            <p className="mt-2 max-w-2xl text-gsr-muted">{today?.reason ?? "The morning desk will publish the next ticker when the pick is set."}</p>
            {today?.sentiment && <p className="mt-2 text-sm text-gsr-accent">{today.sentiment}</p>}
          </div>
          {today?.ticker && (
            <Link
              href={today.research_path || researchHref(today.ticker)}
              className="rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-emerald-400"
            >
              Open full research report
            </Link>
          )}
        </div>
        {subscribed && today?.full_access && today.movers.length > 0 && (
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {today.movers.map((mover) => (
              <Link
                key={String(mover.ticker)}
                href={researchHref(String(mover.ticker || ""))}
                className="rounded-xl border border-gsr-border p-4 hover:border-gsr-accent/40"
              >
                <p className="font-semibold">{mover.ticker}</p>
                <p className="mt-1 text-sm text-gsr-muted">{mover.headline}</p>
              </Link>
            ))}
          </div>
        )}
        {!subscribed && today?.ticker && (
          <p className="mt-4 text-sm text-gsr-muted">
            Guests and Pro users can still open the research report. The full briefing, archive, and unlimited desk are
            part of Newsletter Pro.
          </p>
        )}
      </section>

      {subscribed && (
        <section className="space-y-4">
          <h2 className="text-xl font-semibold">Archive (90 days)</h2>
          {archive.map((item) => (
            <div key={`${item.date}-${item.ticker}`} className="glass-card flex flex-col gap-3 rounded-2xl p-6 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gsr-muted">{formatDate(item.date)}</p>
                <h3 className="mt-1 text-lg font-semibold">{item.ticker}</h3>
                <p className="mt-2 text-gsr-muted">{item.reason}</p>
                <p className="mt-1 text-sm text-gsr-accent">{item.sentiment}</p>
              </div>
              <Link
                href={item.research_path}
                className="rounded-xl border border-gsr-border px-4 py-2 text-sm font-semibold hover:border-gsr-accent"
              >
                View report
              </Link>
            </div>
          ))}
          {archive.length === 0 && <p className="text-sm text-gsr-muted">No briefings in the archive yet.</p>}
        </section>
      )}

      <section className="glass-card rounded-2xl p-8">
        <h2 className="text-xl font-semibold">{weeklyName}</h2>
        <p className="mt-2 text-gsr-muted">{weeklyDescription}</p>
        <SubscribeForm slug={weeklySlug} />
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Weekly issues</h2>
        {issues.map((issue) => (
          <Link
            key={issue.id}
            href={`/newsletter/${issue.id}`}
            className="glass-card block rounded-2xl p-6 transition hover:border-gsr-accent/30"
          >
            <p className="text-sm text-gsr-muted">{formatDate(issue.published_at)}</p>
            <h3 className="mt-1 text-lg font-semibold">{issue.title}</h3>
            <p className="mt-2 text-gsr-muted">{issue.excerpt}</p>
          </Link>
        ))}
        {issues.length === 0 && <p className="text-sm text-gsr-muted">No issues yet.</p>}
      </section>
    </div>
  );
}
