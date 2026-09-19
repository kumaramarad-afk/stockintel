"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { trackEvent } from "@/lib/analytics";

type DataSections = {
  analyst_ratings?: Array<{
    analyst_name?: string;
    action?: string;
    old_rating?: string | null;
    new_rating?: string | null;
    target_price?: number | string | null;
    old_target?: number | string | null;
    date?: string | null;
    direction?: string;
  }>;
  news?: Array<{
    headline?: string;
    source?: string;
    url?: string | null;
    date?: string | null;
    summary?: string;
  }>;
  insider?: Array<{
    executive_name?: string;
    title?: string | null;
    transaction_type?: string;
    shares_quantity?: number | null;
    transaction_value?: number | null;
    date?: string | null;
  }>;
  institutions?: Array<{
    fund_name?: string;
    shares_held?: number | null;
    position_value?: number | null;
    change_percentage?: number | null;
    change_vs_previous_quarter?: number | null;
  }>;
  earnings?: Array<{
    earnings_date?: string | null;
    days_away?: number | null;
    eps_estimate?: number | null;
    previous_eps?: number | null;
    revenue_estimate?: number | null;
    time_of_day?: string | null;
  }>;
  disclaimers?: Record<string, string>;
  empty_labels?: Record<string, string | null>;
};

function money(value: number | string | null | undefined) {
  if (value == null || value === "") return "—";
  const n = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(n)) return String(value);
  if (Math.abs(n) >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function shares(value: number | null | undefined) {
  if (value == null || !Number.isFinite(value)) return "—";
  return value.toLocaleString();
}

function shortDate(value: string | null | undefined) {
  if (!value) return "";
  try {
    return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return value;
  }
}

function SectionShell({
  id,
  title,
  disclaimer,
  children,
  empty,
}: {
  id: string;
  title: string;
  disclaimer?: string;
  children: ReactNode;
  empty?: boolean;
}) {
  const ref = useRef<HTMLElement | null>(null);
  useEffect(() => {
    const node = ref.current;
    if (!node || typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          trackEvent("report_section_viewed", { section: id });
          observer.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [id]);

  return (
    <section ref={ref} className="mt-8">
      <hr className="mb-6 border-slate-200" />
      <h2 className="text-xl font-semibold text-emerald-900">{title}</h2>
      <div className="mt-3">{empty ? <p className="text-sm text-slate-500">No recent activity</p> : children}</div>
      {disclaimer ? <p className="mt-4 text-xs leading-5 text-slate-400">{disclaimer}</p> : null}
    </section>
  );
}

export function ReportDataSections({
  ticker,
  data,
}: {
  ticker: string;
  data?: DataSections | null;
}) {
  if (!data) return null;
  const d = data.disclaimers || {};

  return (
    <div className="space-y-2">
      <SectionShell
        id="analyst_ratings"
        title="8. Analyst ratings & targets"
        disclaimer={d.analyst_ratings}
        empty={!data.analyst_ratings?.length}
      >
        <ul className="space-y-2 text-sm text-slate-800">
          {data.analyst_ratings?.map((row, index) => {
            const up = row.direction === "up" || /up/i.test(String(row.action || ""));
            return (
              <li key={`${row.analyst_name}-${index}`} className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
                <span className="text-slate-500">{shortDate(row.date)}</span>
                <span className="mx-2 text-slate-300">|</span>
                <span className="font-medium">{row.analyst_name}</span>
                <span className={`ml-2 font-semibold ${up ? "text-emerald-700" : "text-rose-700"}`}>
                  {row.action || (up ? "Upgraded" : "Downgraded")}
                </span>
                {(row.old_rating || row.new_rating) && (
                  <span className="ml-2 text-slate-600">
                    {row.old_rating || "—"} → {row.new_rating || "—"}
                  </span>
                )}
                {row.target_price != null && (
                  <span className="ml-2 text-slate-600">Target: {money(row.target_price)}</span>
                )}
              </li>
            );
          })}
        </ul>
      </SectionShell>

      <SectionShell id="news" title="9. Important news" disclaimer={d.news} empty={!data.news?.length}>
        <ul className="space-y-3 text-sm text-slate-800">
          {data.news?.map((row, index) => (
            <li key={`${row.url || row.headline}-${index}`}>
              <p>
                <span className="text-slate-500">{shortDate(row.date)}</span>
                <span className="mx-2 text-slate-300">|</span>
                {row.url ? (
                  <a href={row.url} target="_blank" rel="noreferrer" className="font-medium text-emerald-800 hover:underline">
                    {row.headline}
                  </a>
                ) : (
                  <span className="font-medium">{row.headline}</span>
                )}
                {row.source ? <span className="ml-2 text-slate-500">({row.source})</span> : null}
              </p>
              {row.summary ? <p className="mt-1 text-slate-600">{row.summary}</p> : null}
            </li>
          ))}
        </ul>
      </SectionShell>

      <SectionShell
        id="insider_activity"
        title="10. Insider Form 4 activity"
        disclaimer={d.insider}
        empty={!data.insider?.length}
      >
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm text-slate-800">
            <thead className="text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="py-2 pr-3">Date</th>
                <th className="py-2 pr-3">Executive</th>
                <th className="py-2 pr-3">Action</th>
                <th className="py-2 pr-3">Shares</th>
                <th className="py-2">Value</th>
              </tr>
            </thead>
            <tbody>
              {data.insider?.map((row, index) => {
                const buy = row.transaction_type === "buy";
                return (
                  <tr key={`${row.executive_name}-${index}`} className="border-t border-slate-100">
                    <td className="py-2 pr-3 whitespace-nowrap">{shortDate(row.date)}</td>
                    <td className="py-2 pr-3">
                      {row.executive_name}
                      {row.title ? <span className="text-slate-500"> ({row.title})</span> : null}
                    </td>
                    <td className={`py-2 pr-3 font-semibold ${buy ? "text-emerald-700" : "text-rose-700"}`}>
                      {buy ? "Buy" : "Sell"}
                    </td>
                    <td className="py-2 pr-3">{shares(row.shares_quantity ?? null)}</td>
                    <td className="py-2">{money(row.transaction_value)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </SectionShell>

      <SectionShell
        id="institutional_holdings"
        title="11. Institutional 13F holdings"
        disclaimer={d.institutions}
        empty={!data.institutions?.length}
      >
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm text-slate-800">
            <thead className="text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="py-2 pr-3">Fund</th>
                <th className="py-2 pr-3">Shares</th>
                <th className="py-2 pr-3">Position</th>
                <th className="py-2">Change</th>
              </tr>
            </thead>
            <tbody>
              {data.institutions?.map((row, index) => (
                <tr key={`${row.fund_name}-${index}`} className="border-t border-slate-100">
                  <td className="py-2 pr-3 font-medium">{row.fund_name}</td>
                  <td className="py-2 pr-3">{shares(row.shares_held ?? null)}</td>
                  <td className="py-2 pr-3">{money(row.position_value)}</td>
                  <td className="py-2">
                    {row.change_percentage != null
                      ? `${Number(row.change_percentage) > 0 ? "+" : ""}${Number(row.change_percentage).toFixed(1)}%`
                      : row.change_vs_previous_quarter != null
                        ? shares(row.change_vs_previous_quarter)
                        : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </SectionShell>

      <SectionShell id="earnings" title="12. Earnings this week" disclaimer={d.earnings} empty={!data.earnings?.length}>
        <ul className="space-y-2 text-sm text-slate-800">
          {data.earnings?.map((row, index) => (
            <li key={`${row.earnings_date}-${index}`} className="rounded-lg border border-slate-100 bg-slate-50 px-3 py-2">
              <span className="font-medium">{shortDate(row.earnings_date)}</span>
              {row.days_away != null ? <span className="ml-2 text-slate-500">({row.days_away}d)</span> : null}
              <span className="mx-2 text-slate-300">|</span>
              <span>Consensus EPS: {row.eps_estimate != null ? `$${Number(row.eps_estimate).toFixed(2)}` : "—"}</span>
              <span className="mx-2 text-slate-300">|</span>
              <span>Previous: {row.previous_eps != null ? `$${Number(row.previous_eps).toFixed(2)}` : "—"}</span>
              {row.revenue_estimate != null ? (
                <>
                  <span className="mx-2 text-slate-300">|</span>
                  <span>Revenue est: {money(row.revenue_estimate)}</span>
                </>
              ) : null}
              {row.time_of_day ? <span className="ml-2 text-slate-500">({row.time_of_day})</span> : null}
              <span className="ml-2 text-slate-400">{ticker}</span>
            </li>
          ))}
        </ul>
      </SectionShell>
    </div>
  );
}
