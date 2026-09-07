"use client";

import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "@/components/layout/AuthProvider";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function AuthModal() {
  const { user, authModalOpen, closeAuthModal, login, register, startOAuth } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signup");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [providers, setProviders] = useState({ google: true, apple: true });

  useEffect(() => {
    if (user && authModalOpen) closeAuthModal();
  }, [user, authModalOpen, closeAuthModal]);

  useEffect(() => {
    fetch(`${API_URL}/api/v1/auth/providers`)
      .then((response) => response.json())
      .then((payload) => setProviders({ google: Boolean(payload.google), apple: Boolean(payload.apple) }))
      .catch(() => undefined);
  }, []);

  if (!authModalOpen) return null;

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "signup") await register(fullName || email.split("@")[0], email, password);
      else await login(email, password);
      closeAuthModal();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not authenticate");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-gsr-border bg-gsr-card p-6 shadow-glass">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">Sign in to view full report</h2>
            <p className="mt-2 text-sm text-gsr-muted">Create a free account to unlock 5 free reports every month.</p>
          </div>
          <button type="button" onClick={closeAuthModal} className="text-gsr-muted hover:text-white" aria-label="Close">
            ✕
          </button>
        </div>
        <div className="mt-5 space-y-3">
          <button
            type="button"
            onClick={() => startOAuth("google")}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-gsr-border bg-black/30 px-4 py-3 text-sm font-semibold hover:border-gsr-accent"
          >
            Continue with Google
          </button>
          <button
            type="button"
            onClick={() => startOAuth("apple")}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-gsr-border bg-black/30 px-4 py-3 text-sm font-semibold hover:border-gsr-accent"
          >
            Continue with Apple
          </button>
          {!providers.google && !providers.apple ? null : null}
          <div className="flex items-center gap-3 text-xs uppercase tracking-[0.16em] text-gsr-muted">
            <span className="h-px flex-1 bg-gsr-border" />
            or email
            <span className="h-px flex-1 bg-gsr-border" />
          </div>
        </div>
        <form onSubmit={onSubmit} className="mt-4 space-y-3">
          {mode === "signup" && (
            <input
              required
              value={fullName}
              onChange={(event) => setFullName(event.target.value)}
              placeholder="Full name"
              className="w-full rounded-xl border border-gsr-border bg-black/30 px-4 py-3 outline-none focus:border-gsr-accent"
            />
          )}
          <input
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="Email"
            className="w-full rounded-xl border border-gsr-border bg-black/30 px-4 py-3 outline-none focus:border-gsr-accent"
          />
          <input
            type="password"
            required
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={mode === "signup" ? "Password (8+ characters)" : "Password"}
            className="w-full rounded-xl border border-gsr-border bg-black/30 px-4 py-3 outline-none focus:border-gsr-accent"
          />
          {error && <p className="text-sm text-rose-400">{error}</p>}
          <button type="submit" disabled={busy} className="w-full rounded-xl bg-gsr-accent py-3 font-semibold text-gsr-bg hover:brightness-110 disabled:opacity-60">
            {busy ? "Please wait…" : mode === "signup" ? "Create free account" : "Sign in"}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-gsr-muted">
          {mode === "signup" ? "Already have an account?" : "Need an account?"}{" "}
          <button type="button" className="text-gsr-accent" onClick={() => setMode(mode === "signup" ? "signin" : "signup")}>
            {mode === "signup" ? "Sign in" : "Create one"}
          </button>
        </p>
      </div>
    </div>
  );
}
