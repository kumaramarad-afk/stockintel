"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import { apiUrl } from "@/lib/api";

const TOPICS = [
  { value: "billing", label: "Billing & subscriptions" },
  { value: "research", label: "Research desk" },
  { value: "newsletter", label: "Daily briefing" },
  { value: "account", label: "Account access" },
  { value: "other", label: "General inquiry" },
] as const;

export default function ContactPage() {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [topic, setTopic] = useState<(typeof TOPICS)[number]["value"]>("other");
  const [message, setMessage] = useState("");
  const [company, setCompany] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(apiUrl("/api/v1/contact"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          full_name: fullName,
          email,
          topic,
          message,
          company,
        }),
      });
      if (!response.ok) {
        let detail = "Could not send your message";
        try {
          const payload = (await response.json()) as { detail?: unknown };
          if (typeof payload.detail === "string") detail = payload.detail;
        } catch {
          // keep fallback
        }
        throw new Error(detail);
      }
      setSent(true);
      setFullName("");
      setEmail("");
      setMessage("");
      setTopic("other");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send your message");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="py-4">
      <div className="mx-auto max-w-3xl text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gsr-accent">Contact</p>
        <h1 className="mt-3 text-4xl font-semibold">How can we help?</h1>
        <p className="mt-3 text-gsr-muted">
          Billing, research access, and briefing questions go to the same desk. We reply from{" "}
          <a href="mailto:support@getstockreport.com" className="text-gsr-accent hover:underline">
            support@getstockreport.com
          </a>
          .
        </p>
      </div>

      <div className="mx-auto mt-10 grid max-w-5xl gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.2fr)]">
        <aside className="glass-card space-y-6 rounded-2xl p-6">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-gsr-muted">Email</p>
            <a href="mailto:support@getstockreport.com" className="mt-1 block text-lg font-semibold text-gsr-accent hover:underline">
              support@getstockreport.com
            </a>
            <p className="mt-2 text-sm text-gsr-muted">Typical response time is one to two business days.</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-gsr-muted">Hours</p>
            <p className="mt-1 text-sm text-gsr-muted">Monday–Friday, 9:00–18:00 Eastern Time. Messages sent on weekends are answered on the next business day.</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-gsr-muted">What we can help with</p>
            <ul className="mt-2 space-y-2 text-sm text-gsr-muted">
              <li>Premium billing, invoices, and cancellations</li>
              <li>Research report access and monthly free quota</li>
              <li>Daily briefing delivery and archive</li>
              <li>Account sign-in and email preferences</li>
            </ul>
          </div>
          <p className="text-xs text-gsr-muted">
            GetStockReport is educational and informational only. We do not provide investment advice. See the{" "}
            <Link href="/legal/newsletter-disclaimer" className="text-gsr-accent hover:underline">
              newsletter disclaimer
            </Link>{" "}
            and{" "}
            <Link href="/terms" className="text-gsr-accent hover:underline">
              Terms of Use
            </Link>
            .
          </p>
        </aside>

        <section className="glass-card rounded-2xl p-6">
          {sent ? (
            <div className="space-y-3 py-8 text-center">
              <h2 className="text-2xl font-semibold">Message received</h2>
              <p className="text-gsr-muted">
                Thank you. We will reply from support@getstockreport.com. If you do not see a response, check spam or
                write us directly.
              </p>
              <button
                type="button"
                onClick={() => setSent(false)}
                className="mt-4 rounded-xl border border-gsr-border px-5 py-2.5 text-sm hover:border-gsr-accent"
              >
                Send another message
              </button>
            </div>
          ) : (
            <>
              <h2 className="text-xl font-semibold">Send a message</h2>
              <p className="mt-1 text-sm text-gsr-muted">Include your account email if this is about billing or access.</p>
              <form onSubmit={(event) => void onSubmit(event)} className="mt-6 space-y-4">
                <label className="hidden">
                  Company
                  <input
                    tabIndex={-1}
                    autoComplete="off"
                    value={company}
                    onChange={(event) => setCompany(event.target.value)}
                  />
                </label>
                <div className="grid gap-4 sm:grid-cols-2">
                  <label className="block text-sm">
                    <span className="text-gsr-muted">Full name</span>
                    <input
                      required
                      minLength={2}
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      className="mt-1 w-full rounded-xl border border-gsr-border bg-black/30 px-4 py-3 outline-none focus:border-gsr-accent"
                    />
                  </label>
                  <label className="block text-sm">
                    <span className="text-gsr-muted">Email</span>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(event) => setEmail(event.target.value)}
                      className="mt-1 w-full rounded-xl border border-gsr-border bg-black/30 px-4 py-3 outline-none focus:border-gsr-accent"
                    />
                  </label>
                </div>
                <label className="block text-sm">
                  <span className="text-gsr-muted">Topic</span>
                  <select
                    value={topic}
                    onChange={(event) => setTopic(event.target.value as (typeof TOPICS)[number]["value"])}
                    className="mt-1 w-full rounded-xl border border-gsr-border bg-black/30 px-4 py-3 outline-none focus:border-gsr-accent"
                  >
                    {TOPICS.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm">
                  <span className="text-gsr-muted">Message</span>
                  <textarea
                    required
                    minLength={20}
                    rows={7}
                    value={message}
                    onChange={(event) => setMessage(event.target.value)}
                    placeholder="Share the account email, ticker, or billing detail we should look up."
                    className="mt-1 w-full rounded-xl border border-gsr-border bg-black/30 px-4 py-3 outline-none focus:border-gsr-accent"
                  />
                </label>
                {error && <p className="text-sm text-rose-400">{error}</p>}
                <button
                  type="submit"
                  disabled={busy}
                  className="rounded-xl bg-gsr-accent px-5 py-3 text-sm font-semibold text-gsr-bg hover:brightness-110 disabled:opacity-60"
                >
                  {busy ? "Sending…" : "Send message"}
                </button>
              </form>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
