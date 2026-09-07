import { ReactNode } from "react";

import { scoreBarColor, scoreColor } from "@/lib/format";

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-6 text-sm text-gsr-muted">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-white/10 border-t-gsr-accent" />
      {label ?? "Loading…"}
    </div>
  );
}

export function Unavailable() {
  return <p className="py-4 text-sm text-gsr-muted">Data unavailable</p>;
}

export function YesNo({ value }: { value: boolean | null | undefined }) {
  if (value === null || value === undefined) {
    return <span className="rounded-full border border-gsr-border px-2.5 py-0.5 text-xs text-gsr-muted">N/A</span>;
  }
  return (
    <span
      className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
        value ? "bg-gsr-accent/15 text-gsr-accent" : "bg-rose-500/15 text-rose-400"
      }`}
    >
      {value ? "YES" : "NO"}
    </span>
  );
}

export function Metric({
  label,
  value,
  className,
}: {
  label: string;
  value: ReactNode;
  className?: string;
}) {
  return (
    <div className="rounded-xl border border-gsr-border/80 bg-black/20 px-4 py-3">
      <p className="text-[11px] uppercase tracking-[0.16em] text-gsr-muted">{label}</p>
      <p className={`mt-1.5 text-base font-semibold text-white ${className ?? ""}`}>{value}</p>
    </div>
  );
}

export function ScoreBar({ label, score }: { label: string; score: number | null }) {
  const width = score == null ? 0 : Math.max(0, Math.min(100, score));
  return (
    <div>
      <div className="mb-1.5 flex items-center justify-between text-sm">
        <span className="text-gsr-muted">{label}</span>
        <span className={`font-semibold ${scoreColor(score)}`}>{score == null ? "—" : score}</span>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-black/40">
        <div
          className={`h-full rounded-full transition-all duration-700 ${scoreBarColor(score)}`}
          style={{ width: `${width}%` }}
        />
      </div>
    </div>
  );
}

export function ChevronCard({
  title,
  icon,
  open,
  onToggle,
  loading,
  children,
}: {
  title: string;
  icon?: ReactNode;
  open: boolean;
  onToggle: () => void;
  loading?: boolean;
  children: ReactNode;
}) {
  return (
    <section className="glass-card overflow-hidden rounded-2xl transition hover:border-gsr-accent/25">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left"
        aria-expanded={open}
      >
        <span className="flex items-center gap-3 text-lg font-semibold">
          {icon ? <span className="text-gsr-accent">{icon}</span> : null}
          {title}
          {loading ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/15 border-t-gsr-accent" /> : null}
        </span>
        <svg
          className={`h-5 w-5 shrink-0 text-gsr-muted transition-transform duration-300 ${open ? "rotate-180" : "rotate-0"}`}
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 111.06 1.06l-4.24 4.24a.75.75 0 01-1.06 0L5.21 8.29a.75.75 0 01.02-1.08z"
            clipRule="evenodd"
          />
        </svg>
      </button>
      <div className={`grid transition-[grid-template-rows] duration-300 ease-out ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
        <div className="overflow-hidden">
          <div className="border-t border-gsr-border px-5 py-4">{children}</div>
        </div>
      </div>
    </section>
  );
}

export function SectionIcon({ d }: { d: string }) {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path strokeLinecap="round" strokeLinejoin="round" d={d} />
    </svg>
  );
}

export function Stars({ value }: { value: number | null | undefined }) {
  const count = Math.max(0, Math.min(5, Math.round(value ?? 0)));
  return (
    <span className="tracking-tight text-amber-300" aria-label={`${count} of 5 stars`}>
      {"★".repeat(count)}
      <span className="text-white/20">{"☆".repeat(5 - count)}</span>
    </span>
  );
}

export function daysAgoLabel(days: number | null | undefined) {
  if (days == null) return "—";
  if (days <= 0) return "Today";
  if (days === 1) return "1 day ago";
  return `${days} days ago`;
}
