"use client";

import { FormEvent, useEffect, useState } from "react";

import { apiUrl } from "@/lib/api";

type ExceptionRow = {
  email: string;
  plan: string;
  note: string | null;
  created_at: string | null;
  has_account: boolean;
};

export function PlanExceptionAdmin({ token }: { token: string }) {
  const [rows, setRows] = useState<ExceptionRow[]>([]);
  const [email, setEmail] = useState("");
  const [note, setNote] = useState("Complimentary Premium ($12)");
  const [status, setStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    const response = await fetch(apiUrl("/api/v1/admin/plan-exceptions"), {
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });
    if (!response.ok) throw new Error("Could not load the exception list");
    setRows((await response.json()) as ExceptionRow[]);
  }

  useEffect(() => {
    void load().catch((err) => setStatus(err instanceof Error ? err.message : "Could not load exceptions"));
    // token is the only input that should refetch
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setStatus(null);
    try {
      const response = await fetch(apiUrl("/api/v1/admin/plan-exceptions"), {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ email, note }),
      });
      if (!response.ok) throw new Error("Could not add that email");
      setEmail("");
      await load();
      setStatus("Added as complimentary Premium ($12).");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not add that email");
    } finally {
      setBusy(false);
    }
  }

  async function onRemove(address: string) {
    setBusy(true);
    setStatus(null);
    try {
      const response = await fetch(apiUrl(`/api/v1/admin/plan-exceptions?email=${encodeURIComponent(address)}`), {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) throw new Error("Could not remove that email");
      await load();
      setStatus("Removed from the exception list.");
    } catch (err) {
      setStatus(err instanceof Error ? err.message : "Could not remove that email");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="glass-card mt-6 space-y-4 rounded-2xl p-6">
      <div>
        <h2 className="text-xl font-semibold">Complimentary Premium list</h2>
        <p className="mt-1 text-sm text-gsr-muted">
          Emails on this list are treated as $12 Premium: unlimited research, the daily briefing, and the archive.
        </p>
      </div>
      <form onSubmit={(event) => void onSubmit(event)} className="grid gap-3 sm:grid-cols-[1fr_auto]">
        <input
          type="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="email@example.com"
          className="rounded-xl border border-gsr-border bg-black/20 px-4 py-2.5 text-sm outline-none focus:border-gsr-accent"
        />
        <button
          type="submit"
          disabled={busy}
          className="rounded-xl bg-gsr-accent px-5 py-2.5 text-sm font-semibold text-gsr-bg hover:brightness-110 disabled:opacity-60"
        >
          {busy ? "Saving…" : "Add as Premium"}
        </button>
        <input
          type="text"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Note"
          className="rounded-xl border border-gsr-border bg-black/20 px-4 py-2.5 text-sm outline-none focus:border-gsr-accent sm:col-span-2"
        />
      </form>
      <ul className="space-y-2 text-sm">
        {rows.map((row) => (
          <li key={row.email} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-gsr-border px-4 py-3">
            <div>
              <p className="font-semibold">{row.email}</p>
              <p className="text-gsr-muted">
                {row.note || "Complimentary Premium ($12)"}
                {row.has_account ? " · account exists" : " · no account yet"}
              </p>
            </div>
            <button
              type="button"
              disabled={busy}
              onClick={() => void onRemove(row.email)}
              className="rounded-xl border border-rose-400/40 px-3 py-1.5 text-rose-200 hover:border-rose-300 disabled:opacity-60"
            >
              Remove
            </button>
          </li>
        ))}
        {rows.length === 0 && <li className="text-gsr-muted">No complimentary emails yet.</li>}
      </ul>
      {status && <p className="text-sm text-gsr-muted">{status}</p>}
    </div>
  );
}
