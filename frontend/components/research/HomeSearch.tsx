"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { apiUrl } from "@/lib/api";

type SearchHit = {
  ticker: string;
  name?: string | null;
};

type HomeSearchProps = {
  className?: string;
  buttonLabel?: string;
  placeholder?: string;
};

export function HomeSearch({
  className,
  buttonLabel = "Open report",
  placeholder = "Search any ticker or company (Apple, AAPL, NVIDIA…)",
}: HomeSearchProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [active, setActive] = useState(0);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onDocClick(event: MouseEvent) {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    const needle = query.trim();
    if (needle.length < 1) {
      setHits([]);
      setOpen(false);
      return;
    }
    const handle = window.setTimeout(async () => {
      try {
        const response = await fetch(apiUrl(`/api/v1/research/search?q=${encodeURIComponent(needle)}`), {
          cache: "no-store",
        });
        if (!response.ok) return;
        const payload = (await response.json()) as { tickers?: SearchHit[] };
        setHits(payload.tickers || []);
        setOpen(true);
        setActive(0);
      } catch {
        // Search suggestions are best-effort.
      }
    }, 180);
    return () => window.clearTimeout(handle);
  }, [query]);

  const hint = useMemo(() => hits[active] || hits[0], [active, hits]);

  async function go(symbolOrQuery: string) {
    const raw = symbolOrQuery.trim();
    if (!raw) return;
    setBusy(true);
    try {
      const response = await fetch(apiUrl(`/api/v1/research/resolve?q=${encodeURIComponent(raw)}`), {
        cache: "no-store",
      });
      if (response.ok) {
        const payload = (await response.json()) as { ticker?: string };
        if (payload.ticker) {
          router.push(`/research/${encodeURIComponent(payload.ticker)}`);
          return;
        }
      }
      router.push(`/research/${encodeURIComponent(raw.toUpperCase())}`);
    } finally {
      setBusy(false);
      setOpen(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void go(hint?.ticker || query);
  }

  return (
    <div ref={boxRef} className={`relative ${className || ""}`}>
      <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onFocus={() => hits.length && setOpen(true)}
          onKeyDown={(event) => {
            if (!open || !hits.length) return;
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setActive((index) => (index + 1) % hits.length);
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              setActive((index) => (index - 1 + hits.length) % hits.length);
            } else if (event.key === "Escape") {
              setOpen(false);
            }
          }}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
          className="flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-100 outline-none ring-emerald-500/40 placeholder:text-slate-500 focus:ring"
        />
        <button
          type="submit"
          disabled={busy || !query.trim()}
          className="rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {busy ? "Opening…" : buttonLabel}
        </button>
      </form>
      {open && hits.length > 0 && (
        <ul className="absolute z-20 mt-2 max-h-72 w-full overflow-auto rounded-xl border border-slate-700 bg-slate-950 shadow-xl">
          {hits.map((hit, index) => (
            <li key={hit.ticker}>
              <button
                type="button"
                onMouseEnter={() => setActive(index)}
                onClick={() => void go(hit.ticker)}
                className={`flex w-full items-baseline justify-between gap-3 px-4 py-3 text-left text-sm ${
                  index === active ? "bg-emerald-500/15 text-slate-50" : "text-slate-300 hover:bg-slate-900"
                }`}
              >
                <span className="font-semibold tracking-wide">{hit.ticker}</span>
                <span className="truncate text-slate-500">{hit.name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
