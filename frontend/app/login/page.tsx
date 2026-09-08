"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/components/layout/AuthProvider";
import { goToResearch, RESEARCH_PATH } from "@/lib/auth";

export default function LoginPage() {
  const { login, startOAuth, user, loading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!loading && user) router.replace(RESEARCH_PATH);
  }, [loading, user, router]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email, password);
      goToResearch();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not sign in");
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md py-10">
      <h1 className="text-3xl font-semibold">Sign in</h1>
      <p className="mt-2 text-gsr-muted">Access your GetStockReport account.</p>
      <form onSubmit={onSubmit} className="glass-card mt-8 space-y-4 rounded-2xl p-6">
        <button type="button" onClick={() => startOAuth("google")} className="w-full rounded-xl border border-gsr-border py-3 text-sm font-semibold hover:border-gsr-accent">
          Continue with Google
        </button>
        <button type="button" onClick={() => startOAuth("apple")} className="w-full rounded-xl border border-gsr-border py-3 text-sm font-semibold hover:border-gsr-accent">
          Continue with Apple
        </button>
        <div className="flex items-center gap-3 text-xs uppercase tracking-[0.16em] text-gsr-muted">
          <span className="h-px flex-1 bg-gsr-border" />
          or email
          <span className="h-px flex-1 bg-gsr-border" />
        </div>
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
        <label className="block text-sm">
          <span className="text-gsr-muted">Password</span>
          <input
            type="password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1 w-full rounded-xl border border-gsr-border bg-black/30 px-4 py-3 outline-none focus:border-gsr-accent"
          />
        </label>
        {error && <p className="text-sm text-rose-400">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-gsr-accent py-3 font-semibold text-gsr-bg hover:brightness-110 disabled:opacity-60"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="mt-4 text-sm text-gsr-muted">
        No account?{" "}
        <Link href="/register" className="text-gsr-accent hover:text-white">
          Create one
        </Link>
      </p>
    </div>
  );
}
