"use client";

import { FormEvent, useState } from "react";

import { apiUrl } from "@/lib/api";

export function SubscribeForm({ slug }: { slug: string }) {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Saving…");
    try {
      const response = await fetch(apiUrl("/api/v1/newsletters/subscribe"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, newsletter_slug: slug }),
      });
      if (!response.ok) throw new Error("Subscribe failed");
      setEmail("");
      setStatus("You are on the list.");
    } catch {
      setStatus("Could not subscribe. Is the API running?");
    }
  }

  return (
    <form onSubmit={onSubmit} className="mt-4 flex flex-col gap-3 sm:flex-row">
      <input
        type="email"
        required
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        placeholder="you@firm.com"
        className="w-full rounded-xl border border-gsr-border bg-black/30 px-4 py-3 text-sm outline-none focus:border-gsr-accent"
      />
      <button
        type="submit"
        className="rounded-xl bg-gsr-accent px-5 py-3 text-sm font-semibold text-gsr-bg hover:brightness-110"
      >
        Subscribe
      </button>
      {status && <p className="self-center text-sm text-slate-300">{status}</p>}
    </form>
  );
}
