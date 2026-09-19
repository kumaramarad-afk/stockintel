"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";

import { apiUrl } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";

export type SearchHit = {
  ticker: string;
  company_name?: string | null;
  name?: string | null;
};

type SearchBoxProps = {
  className?: string;
  buttonLabel?: string;
  placeholder?: string;
  showButton?: boolean;
  debounceMs?: number;
  onResultsChange?: (hits: SearchHit[]) => void;
  /** When true, empty query loads the full catalog (research directory). */
  loadAllWhenEmpty?: boolean;
};

function labelFor(hit: SearchHit) {
  const name = hit.company_name || hit.name;
  return name ? `${hit.ticker} — ${name}` : hit.ticker;
}

export function SearchBox({
  className,
  buttonLabel = "Open report",
  placeholder = "Search by ticker or company…",
  showButton = true,
  debounceMs = 300,
  onResultsChange,
  loadAllWhenEmpty = false,
}: SearchBoxProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [active, setActive] = useState(0);
  const [searched, setSearched] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);
  const lastQuery = useRef("");

  useEffect(() => {
    function onDocClick(event: MouseEvent) {
      if (!boxRef.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  useEffect(() => {
    const needle = query.trim();
    if (!needle && !loadAllWhenEmpty) {
      setHits([]);
      setOpen(false);
      setSearched(false);
      onResultsChange?.([]);
      return;
    }
    let cancelled = false;
    const handle = window.setTimeout(async () => {
      try {
        lastQuery.current = needle;
        const limit = needle ? 10 : 50;
        const response = await fetch(apiUrl(`/api/v1/search?q=${encodeURIComponent(needle)}&limit=${limit}`), {
          cache: "no-store",
        });
        if (!response.ok || cancelled) return;
        const payload = (await response.json()) as SearchHit[];
        const rows = Array.isArray(payload) ? payload : [];
        setHits(rows);
        setSearched(true);
        setOpen(Boolean(needle));
        setActive(0);
        onResultsChange?.(rows);
        if (needle) {
          trackEvent("search", { query: needle, results: rows.length });
        }
      } catch {
        // Search suggestions are best-effort.
      }
    }, debounceMs);
    return () => {
      cancelled = true;
      window.clearTimeout(handle);
    };
  }, [query, debounceMs, loadAllWhenEmpty, onResultsChange]);

  const hint = useMemo(() => hits[active] || hits[0], [active, hits]);

  function selectResult(hit: SearchHit) {
    const symbol = hit.ticker.trim().toUpperCase();
    if (!symbol) return;
    setQuery(symbol);
    setOpen(false);
    setBusy(true);
    trackEvent("search", {
      query: lastQuery.current || query.trim(),
      results: hits.length,
      clicked: symbol,
    });
    router.push(`/research/${encodeURIComponent(symbol)}`);
  }

  async function go(rawInput: string) {
    const raw = rawInput.trim();
    if (!raw) return;
    setBusy(true);
    try {
      const response = await fetch(apiUrl(`/api/v1/search?q=${encodeURIComponent(raw)}&limit=1`), {
        cache: "no-store",
      });
      if (response.ok) {
        const payload = (await response.json()) as SearchHit[];
        if (Array.isArray(payload) && payload[0]?.ticker) {
          selectResult(payload[0]);
          return;
        }
      }
      selectResult({ ticker: raw.toUpperCase() });
    } finally {
      setBusy(false);
    }
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void go(hint?.ticker || query);
  }

  return (
    <div ref={boxRef} className={`relative z-30 w-full ${className || ""}`}>
      <form onSubmit={onSubmit} className={`flex flex-col gap-3 ${showButton ? "sm:flex-row" : ""}`}>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onFocus={() => {
            if (hits.length && query.trim()) setOpen(true);
          }}
          onKeyDown={(event) => {
            if (!open || !hits.length) return;
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setActive((index) => (index + 1) % hits.length);
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              setActive((index) => (index - 1 + hits.length) % hits.length);
            } else if (event.key === "Enter" && hint) {
              event.preventDefault();
              selectResult(hint);
            } else if (event.key === "Escape") {
              setOpen(false);
            }
          }}
          placeholder={placeholder}
          autoComplete="off"
          spellCheck={false}
          className="w-full flex-1 rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-slate-100 outline-none ring-emerald-500/40 placeholder:text-slate-500 focus:ring"
        />
        {showButton ? (
          <button
            type="submit"
            disabled={busy || !query.trim()}
            className="rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-slate-950 hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "Opening…" : buttonLabel}
          </button>
        ) : null}
      </form>
      {open && query.trim() && (
        <ul className="absolute z-50 mt-2 max-h-72 w-full overflow-auto rounded-xl border border-slate-700 bg-slate-950 shadow-xl">
          {hits.length ? (
            hits.map((hit, index) => (
              <li key={hit.ticker}>
                <button
                  type="button"
                  onMouseDown={(event) => {
                    // Prevent input blur from closing before navigation.
                    event.preventDefault();
                    selectResult(hit);
                  }}
                  onMouseEnter={() => setActive(index)}
                  className={`flex w-full items-baseline justify-between gap-3 px-4 py-3 text-left text-sm ${
                    index === active ? "bg-emerald-500/15 text-slate-50" : "text-slate-300 hover:bg-slate-900"
                  }`}
                >
                  <span className="font-semibold tracking-wide">{hit.ticker}</span>
                  <span className="truncate text-slate-500">{hit.company_name || hit.name}</span>
                </button>
              </li>
            ))
          ) : searched ? (
            <li className="px-4 py-3 text-sm text-slate-500">No results</li>
          ) : null}
        </ul>
      )}
      <span className="sr-only">{hint ? labelFor(hint) : ""}</span>
    </div>
  );
}
