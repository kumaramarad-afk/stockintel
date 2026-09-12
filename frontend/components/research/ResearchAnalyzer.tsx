"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { ResearchHero } from "@/components/research/ResearchHero";
import { PaywallLock, UpgradeButton } from "@/components/research/PaywallLock";
import { useAuth } from "@/components/layout/AuthProvider";
import { ChevronCard, Metric, ScoreBar, SectionIcon, Spinner, Stars, Unavailable, YesNo, daysAgoLabel } from "@/components/research/ui";
import { ScoreGauge } from "@/components/research/ScoreGauge";
import {
  formatCompact,
  formatPrice,
  formatRatio,
  formatSigned,
  isPlaceholder,
  scoreColor,
  toneClass,
} from "@/lib/format";
import type {
  AccessInfo,
  AiData,
  AnalystAction,
  AnalystsData,
  DividendsData,
  EarningsData,
  FundamentalsData,
  HeaderData,
  OwnershipData,
  ResearchSection,
  SectionState,
  SectorData,
  SentimentData,
  TechnicalsData,
  TopAnalyst,
} from "@/lib/research";
import { apiUrl } from "@/lib/api";
import { hasNewsletter, isPaidPlan } from "@/lib/plans";

const SECTIONS = [
  "header",
  "ai",
  "technicals",
  "fundamentals",
  "analysts",
  "earnings",
  "sentiment",
  "ownership",
  "dividends",
  "sector",
] as const;

type SectionName = (typeof SECTIONS)[number];

const empty = <T,>(): SectionState<T> => ({ loading: false, error: null, data: null, available: false });

function signalFromScore(score: number | null | undefined) {
  if (score != null && score >= 75) return { label: "BULLISH CONSENSUS", emoji: "🟢", tone: "green" };
  if (score != null && score < 50) return { label: "BEARISH CONSENSUS", emoji: "🔴", tone: "red" };
  return { label: "MIXED SIGNALS", emoji: "🟡", tone: "amber" };
}

function signalClass(tone: string | null | undefined) {
  if (tone === "green") return "border-gsr-accent/40 bg-gsr-accent/10 text-gsr-accent";
  if (tone === "red") return "border-rose-400/40 bg-rose-400/10 text-rose-300";
  return "border-amber-400/40 bg-amber-400/10 text-amber-200";
}

function consensusClass(value: string | null | undefined) {
  const text = (value ?? "").toLowerCase();
  if (text.includes("bullish")) return "text-gsr-accent bg-gsr-accent/10";
  if (text.includes("bearish")) return "text-rose-400 bg-rose-400/10";
  return "text-amber-300 bg-amber-300/10";
}

function sentimentClass(value: string | null | undefined) {
  const text = (value ?? "").toLowerCase();
  if (text === "positive" || text === "bullish" || text === "up" || text === "in") return "text-gsr-accent";
  if (text === "negative" || text === "bearish" || text === "down" || text === "out") return "text-rose-400";
  return "text-amber-300";
}

function pct(value: number | null | undefined) {
  return value == null ? "—" : formatSigned(value, 2, "%");
}

function ratioPct(value: number | string | null | undefined) {
  if (value == null) return "—";
  if (typeof value === "string" && value.includes("$$$")) return value;
  const amount = typeof value === "string" ? Number(value) : value;
  if (Number.isNaN(amount)) return "—";
  const scaled = Math.abs(amount) <= 1.5 ? amount * 100 : amount;
  return `${scaled.toFixed(1)}%`;
}

function asList(value: string | string[] | null | undefined) {
  if (!value) return [];
  if (Array.isArray(value)) return value.map((item) => item.trim()).filter(Boolean);
  return value
    .split(/\n+/)
    .map((item) => item.replace(/^[-•]\s*/, "").trim())
    .filter(Boolean);
}

function publicAction(action: string | null | undefined) {
  const text = (action || "").toLowerCase();
  if (text.includes("sell") || text.includes("sale") || text.includes("disposed")) return "Disposed";
  if (text.includes("buy") || text.includes("purchase") || text.includes("acquired")) return "Acquired";
  return action || "—";
}

function outlookTone(value: string | null | undefined) {
  const text = (value ?? "").toLowerCase();
  if (text.includes("bullish") || text.includes("positive")) return "text-gsr-accent";
  if (text.includes("bearish") || text.includes("negative")) return "text-rose-400";
  return "text-gsr-muted";
}

async function fetchSection<T>(ticker: string, section: SectionName, token: string | null): Promise<ResearchSection<T>> {
  const response = await fetch(apiUrl(`/api/v1/research/report/${encodeURIComponent(ticker)}/${section}`), {
    cache: "no-store",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    signal: AbortSignal.timeout(section === "ai" || section === "ownership" ? 120_000 : 60_000),
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
    } catch {
      // Keep status fallback.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<ResearchSection<T>>;
}

export function ResearchAnalyzer() {
  const { token, user, loading: authLoading, openAuthModal, refreshProfile, startCheckout } = useAuth();
  const [ticker, setTicker] = useState("");
  const [active, setActive] = useState<string | null>(null);
  const [access, setAccess] = useState<AccessInfo | null>(null);
  const [header, setHeader] = useState(empty<HeaderData>());
  const [ai, setAi] = useState(empty<AiData>());
  const [technicals, setTechnicals] = useState(empty<TechnicalsData>());
  const [fundamentals, setFundamentals] = useState(empty<FundamentalsData>());
  const [analysts, setAnalysts] = useState(empty<AnalystsData>());
  const [earnings, setEarnings] = useState(empty<EarningsData>());
  const [sentiment, setSentiment] = useState(empty<SentimentData>());
  const [ownership, setOwnership] = useState(empty<OwnershipData>());
  const [dividends, setDividends] = useState(empty<DividendsData>());
  const [sector, setSector] = useState(empty<SectorData>());
  const [open, setOpen] = useState<Record<string, boolean>>({
    technicals: true,
    fundamentals: false,
    analysts: false,
    earnings: false,
    sentiment: false,
    ownership: false,
    dividends: false,
    sector: false,
  });

  const setters: Record<SectionName, (state: SectionState<never>) => void> = {
    header: setHeader as (state: SectionState<never>) => void,
    ai: setAi as (state: SectionState<never>) => void,
    technicals: setTechnicals as (state: SectionState<never>) => void,
    fundamentals: setFundamentals as (state: SectionState<never>) => void,
    analysts: setAnalysts as (state: SectionState<never>) => void,
    earnings: setEarnings as (state: SectionState<never>) => void,
    sentiment: setSentiment as (state: SectionState<never>) => void,
    ownership: setOwnership as (state: SectionState<never>) => void,
    dividends: setDividends as (state: SectionState<never>) => void,
    sector: setSector as (state: SectionState<never>) => void,
  };

  const load = useCallback(async (symbol: string) => {
    setActive(symbol);
    sessionStorage.setItem("gsr_resume_ticker", symbol);
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("ticker", symbol);
      window.history.replaceState({}, "", `${url.pathname}${url.search}`);
    }
    for (const section of SECTIONS) {
      setters[section]({ loading: true, error: null, data: null, available: false });
    }
    await Promise.all(
      SECTIONS.map(async (section) => {
        try {
          const result = await fetchSection(symbol, section, token);
          if (result.access) setAccess(result.access);
          setters[section]({
            loading: false,
            error: result.available ? null : result.error || "Data unavailable",
            data: result.data as never,
            available: result.available,
          });
        } catch (error) {
          setters[section]({
            loading: false,
            error: error instanceof Error ? error.message : "Data unavailable",
            data: null,
            available: false,
          });
        }
      }),
    );
    await refreshProfile();
  }, [token, refreshProfile]);

  useEffect(() => {
    if (authLoading) return;
    const fromQuery =
      typeof window === "undefined" ? "" : new URLSearchParams(window.location.search).get("ticker")?.trim().toUpperCase();
    if (fromQuery) {
      setTicker(fromQuery);
      void load(fromQuery);
      return;
    }
    if (active) {
      void load(active);
      return;
    }
    const resume = sessionStorage.getItem("gsr_resume_ticker");
    if (resume) {
      setTicker(resume);
      void load(resume);
    }
  }, [authLoading, token, user?.plan]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const symbol = ticker.trim().toUpperCase();
    if (!symbol) return;
    await load(symbol);
  }

  const showReport = Boolean(active);
  const headerData = header.data;
  const showDividends = dividends.loading || dividends.available || Boolean(dividends.data);
  const fieldLocked = (name: string) => Boolean(access?.locked_fields?.includes(name));
  const remaining = Math.max(
    0,
    user?.reports_remaining ??
      access?.reports_remaining ??
      (access?.reports_limit ?? 5) - (access?.reports_used ?? 0),
  );
  const quotaExhausted = Boolean(user && !isPaidPlan(user.plan) && remaining <= 0);
  const quotaLabel =
    user && !isPaidPlan(user.plan) ? `${remaining} / ${user.reports_limit ?? 5} free reports remaining this month` : null;

  return (
    <section className="space-y-8">
      <ResearchHero
        ticker={ticker}
        setTicker={setTicker}
        onSubmit={onSubmit}
        showReport={showReport}
        quotaLabel={quotaLabel}
        quotaExhausted={quotaExhausted}
        onUpgrade={() => {
          void startCheckout();
        }}
        onSelect={(symbol) => {
          setTicker(symbol);
          void load(symbol);
        }}
      />

      {!hasNewsletter(user?.plan) && (
        <div className="flex flex-col gap-3 rounded-2xl border border-amber-400/30 bg-amber-400/10 px-4 py-3 text-sm text-amber-50 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-semibold">Daily market briefing at 8 AM UTC</p>
            <p className="text-amber-100/80">Premium adds the morning desk and a 90-day archive for $12/month, with unlimited research.</p>
          </div>
          <Link
            href="/newsletter"
            className="rounded-xl bg-emerald-500 px-4 py-2 text-center text-sm font-semibold text-slate-950 hover:bg-emerald-400"
          >
            Open newsletter
          </Link>
        </div>
      )}

      {showReport && (
        <div className="space-y-6">
          {access && (
            <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-gsr-border bg-gsr-card px-4 py-3 text-sm">
              {access.pro && (
                <p className="text-gsr-accent">
                  {hasNewsletter(user?.plan)
                    ? "Premium unlocked — full research and the daily briefing are live."
                    : "Premium desk unlocked — full metrics and alerts are live."}
                </p>
              )}
              {access.entitlement === "full" && !access.pro && (
                <p className="text-gsr-muted">{remaining} / {access.reports_limit} free reports remaining this month.</p>
              )}
              {access.entitlement === "public" && user && (
                <p className="text-amber-200">You have used 5 free reports this month. Further reports match the guest preview until you upgrade.</p>
              )}
              {access.entitlement === "public" && !user && (
                <p className="text-gsr-muted">Public preview. Sign in for 5 full reports every month.</p>
              )}
              {access.entitlement !== "full" && (
                <div className="flex flex-wrap gap-2">
                  {!user && (
                    <button type="button" onClick={openAuthModal} className="rounded-xl border border-gsr-border px-4 py-2 font-semibold hover:border-gsr-accent">
                      View Full Analyst Report
                    </button>
                  )}
                  <UpgradeButton />
                </div>
              )}
            </div>
          )}
          {header.loading && <Spinner label="Loading header…" />}
          {!header.loading && !header.available && <p className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{header.error || "Data unavailable"}</p>}
          {headerData && (
            <div className="space-y-6">
              <div className="glass-card rounded-2xl p-6 shadow-glass sm:p-8">
                <div className="flex flex-col items-center gap-8 lg:flex-row lg:items-center">
                  <ScoreGauge score={headerData.composite_score} />
                  <div className="min-w-0 flex-1 space-y-5">
                    <div className="flex flex-wrap items-end justify-between gap-4">
                      <div>
                        <p className="text-sm tracking-[0.2em] text-gsr-muted">{headerData.ticker}</p>
                        <h2 className="mt-1 text-3xl font-semibold sm:text-4xl">{headerData.name ?? headerData.ticker}</h2>
                        <span className={`mt-3 inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs font-semibold tracking-[0.14em] ${signalClass(headerData.signal_tone || signalFromScore(headerData.composite_score).tone)}`}>
                          <span aria-hidden="true">{headerData.signal_emoji || signalFromScore(headerData.composite_score).emoji}</span>
                          {headerData.signal_label || signalFromScore(headerData.composite_score).label}
                        </span>
                      </div>
                      <div className="text-right">
                        <p className="text-3xl font-semibold">{formatPrice(headerData.price)}</p>
                        <p className={toneClass(headerData.change_percent)}>
                          {formatSigned(headerData.change_amount)} ({pct(headerData.change_percent)})
                        </p>
                      </div>
                    </div>
                    <div className="grid gap-3">
                      <ScoreBar label="Fundamental" score={headerData.scores.fundamental} />
                      <ScoreBar label="Technical" score={headerData.scores.technical} />
                      <ScoreBar label="Analyst" score={headerData.scores.analyst} />
                      <ScoreBar label="Institutional" score={headerData.scores.institutional} />
                      <ScoreBar label="Sentiment" score={headerData.scores.sentiment} />
                    </div>
                    {headerData.risk_flags.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {headerData.risk_flags.map((flag) => (
                          <span key={flag} className="rounded-full border border-amber-400/30 bg-amber-400/10 px-3 py-1 text-xs font-medium text-amber-200">
                            {flag.replace("WARNING: ", "")}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>

              <AnalystConsensusCard
                bullish={headerData.bullish_count}
                neutral={headerData.neutral_count}
                bearish={headerData.bearish_count}
                price={headerData.price}
                averageTarget={headerData.average_target}
                upsidePct={headerData.upside_pct}
                lockTargets={fieldLocked("targets")}
              />

              <RecentActionsFeed actions={headerData.recent_actions || []} lockTargets={fieldLocked("targets") || fieldLocked("direction")} />
              <TopAnalystsList analysts={headerData.top_analysts || []} lockCase={fieldLocked("analyst_case")} />
            </div>
          )}

          <article className="glass-card rounded-2xl border-l-4 border-l-gsr-accent p-6 sm:p-7">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-gsr-accent">Research briefing</p>
            {ai.loading && <Spinner label="Writing research briefing…" />}
            {!ai.loading && !ai.available && <Unavailable />}
            {ai.data && (
              <div className="mt-5 space-y-6 text-[15px] leading-7 text-white/90">
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-gsr-muted">What the data shows</h3>
                  <PaywallLock locked={fieldLocked("summary") && !(ai.data.summary_preview || ai.data.what_the_data_shows)} minHeight="min-h-[6rem]">
                    <p className="mt-2">{ai.data.summary_preview || ai.data.what_the_data_shows || ai.data.why_it_scores || "Sign in to read the briefing."}</p>
                  </PaywallLock>
                  {fieldLocked("summary") && (ai.data.summary_preview || ai.data.what_the_data_shows) && access?.entitlement === "basic" && (
                    <div className="relative mt-2">
                      <p className="paywall-blur pointer-events-none select-none text-gsr-muted">Additional briefing detail is reserved for the Pro desk and is not included in this snapshot.</p>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <UpgradeButton />
                      </div>
                    </div>
                  )}
                </section>
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-gsr-muted">Key risks to monitor</h3>
                  <PaywallLock locked={fieldLocked("risks")} minHeight="min-h-[8rem]">
                    <ul className="mt-2 list-disc space-y-1 pl-5">
                      {asList(ai.data.key_risks).map((item, idx) => (
                        <li key={`risk-${idx}`}>{item}</li>
                      ))}
                      {asList(ai.data.key_risks).length === 0 && <li className="text-gsr-muted">No automated risk items were published on this snapshot.</li>}
                    </ul>
                  </PaywallLock>
                </section>
                <section>
                  <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-gsr-muted">Upcoming catalysts</h3>
                  <PaywallLock locked={fieldLocked("catalysts")} minHeight="min-h-[8rem]">
                    <ul className="mt-2 list-disc space-y-1 pl-5">
                      {(ai.data.upcoming_catalysts || []).map((item) => (
                        <li key={item}>{item}</li>
                      ))}
                      {(ai.data.upcoming_catalysts || []).length === 0 && <li className="text-gsr-muted">No dated catalysts were published on this snapshot.</li>}
                    </ul>
                  </PaywallLock>
                </section>
                <div className="flex flex-wrap items-center gap-3 rounded-xl border border-gsr-border bg-black/20 px-4 py-3 text-sm">
                  <span className="text-gsr-muted">Options snapshot</span>
                  <YesNo value={ai.data.options_opportunity} />
                  <span className="text-gsr-muted">
                    Implied {pct(ai.data.implied_move)} vs historical {pct(ai.data.historical_move)}
                  </span>
                </div>
                <p className="text-xs text-gsr-muted">{ai.data.disclaimer || "Data sourced from public analyst reports. Not financial advice."}</p>
              </div>
            )}
          </article>

          <ChevronCard title="Price & Technicals" icon={<SectionIcon d="M3 17l6-6 4 4 8-8" />} open={open.technicals} onToggle={() => setOpen((s) => ({ ...s, technicals: !s.technicals }))} loading={technicals.loading}>
            {technicals.loading && <Spinner />}
            {!technicals.loading && !technicals.available && <Unavailable />}
            {technicals.data && (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                <Metric label="Price" value={formatPrice(technicals.data.price)} />
                <Metric label="Open" value={formatPrice(technicals.data.open)} />
                <Metric label="High" value={formatPrice(technicals.data.high)} />
                <Metric label="Low" value={formatPrice(technicals.data.low)} />
                <Metric label="52-week high" value={`${formatPrice(technicals.data.week_52_high)} (${pct(technicals.data.pct_from_52w_high)})`} className={toneClass(technicals.data.pct_from_52w_high)} />
                <Metric label="52-week low" value={`${formatPrice(technicals.data.week_52_low)} (${pct(technicals.data.pct_from_52w_low)})`} className={toneClass(technicals.data.pct_from_52w_low)} />
                <Metric label="Volume vs 30d avg" value={`${formatCompact(technicals.data.volume)} / ${formatCompact(technicals.data.volume_avg_30d)} (${pct(technicals.data.volume_vs_avg_pct)})`} />
                <Metric label="50 MA" value={`${formatPrice(technicals.data.ma50)} · ${technicals.data.above_ma50 == null ? "—" : technicals.data.above_ma50 ? "Above" : "Below"}`} className={toneClass(technicals.data.above_ma50)} />
                <Metric label="200 MA" value={`${formatPrice(technicals.data.ma200)} · ${technicals.data.above_ma200 == null ? "—" : technicals.data.above_ma200 ? "Above" : "Below"}`} className={toneClass(technicals.data.above_ma200)} />
                <Metric label="Cross alert" value={technicals.data.cross_alert === "golden_cross" ? "Golden cross" : technicals.data.cross_alert === "death_cross" ? "Death cross" : "None"} className={technicals.data.cross_alert === "golden_cross" ? "text-gsr-accent" : technicals.data.cross_alert === "death_cross" ? "text-rose-400" : "text-amber-300"} />
                <Metric label="RSI" value={`${formatRatio(technicals.data.rsi)} · ${technicals.data.rsi_label ?? "—"}`} className={technicals.data.rsi_label === "healthy" ? "text-gsr-accent" : technicals.data.rsi_label === "overbought" ? "text-rose-400" : technicals.data.rsi_label === "oversold" ? "text-amber-300" : ""} />
                <Metric label="MACD" value={technicals.data.macd_signal ?? "—"} className={technicals.data.macd_signal === "bullish" ? "text-gsr-accent" : "text-rose-400"} />
                <Metric label="Bollinger squeeze" value={<YesNo value={technicals.data.bollinger_squeeze} />} />
                <Metric label="Support" value={formatPrice(technicals.data.support)} />
                <Metric label="Resistance" value={formatPrice(technicals.data.resistance)} />
                <Metric label="Pattern" value={technicals.data.pattern ?? "None detected"} />
              </div>
            )}
          </ChevronCard>

          <ChevronCard title="Fundamentals" icon={<SectionIcon d="M4 19h16M7 16V8m5 8V4m5 12v-6" />} open={open.fundamentals} onToggle={() => setOpen((s) => ({ ...s, fundamentals: !s.fundamentals }))} loading={fundamentals.loading}>
            {fundamentals.loading && <Spinner />}
            {!fundamentals.loading && !fundamentals.available && <Unavailable />}
            {fundamentals.data && (
              <div className="space-y-5">
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Metric label="Revenue acceleration" value={<YesNo value={fundamentals.data.revenue_acceleration} />} />
                  <Metric label="Beat streak" value={fundamentals.data.beat_streak ?? "—"} />
                  <Metric label="Gross margin" value={`${ratioPct(fundamentals.data.gross_margin)} · ${fundamentals.data.gross_margin_trend ?? "—"}`} />
                  <Metric label="Operating margin" value={ratioPct(fundamentals.data.operating_margin)} />
                  <Metric label="Free cash flow positive" value={<YesNo value={fundamentals.data.free_cash_flow_positive} />} />
                  <Metric label="Debt / equity" value={formatRatio(fundamentals.data.debt_to_equity)} />
                  <Metric label="ROE" value={ratioPct(fundamentals.data.return_on_equity)} />
                  <Metric label="P/E vs sector" value={`${formatRatio(fundamentals.data.pe_ratio)} vs ${fundamentals.data.sector_pe == null ? "Data unavailable" : formatRatio(fundamentals.data.sector_pe)}`} />
                  <Metric label="PEG" value={formatRatio(fundamentals.data.peg_ratio)} />
                  <Metric label="Price / sales" value={formatRatio(fundamentals.data.price_to_sales)} />
                  <Metric label="Price / book" value={formatRatio(fundamentals.data.price_to_book)} />
                  <Metric label="EV/EBITDA" value={formatRatio(fundamentals.data.ev_ebitda)} />
                </div>
                <div className="overflow-x-auto">
                  <p className="mb-2 text-sm font-medium text-slate-300">Revenue last 4 quarters</p>
                  <table className="w-full text-left text-sm">
                    <thead className="text-slate-400"><tr><th className="py-2">Period</th><th>Revenue</th><th>Growth</th></tr></thead>
                    <tbody>
                      {(fundamentals.data.revenue_quarters || []).map((row, idx) => (
                        <tr key={idx} className="border-t border-white/5">
                          <td className="py-2">{row.period ?? "—"}</td>
                          <td>{formatCompact(row.revenue)}</td>
                          <td className={toneClass(row.growth_pct)}>{pct(row.growth_pct)}</td>
                        </tr>
                      ))}
                      {(fundamentals.data.revenue_quarters || []).length === 0 && <tr><td className="py-3 text-slate-400" colSpan={3}>Data unavailable</td></tr>}
                    </tbody>
                  </table>
                </div>
                <div className="overflow-x-auto">
                  <p className="mb-2 text-sm font-medium text-slate-300">EPS last 8 quarters</p>
                  <table className="w-full text-left text-sm">
                    <thead className="text-slate-400"><tr><th className="py-2">Quarter</th><th>Est</th><th>Actual</th><th>Beat?</th></tr></thead>
                    <tbody>
                      {(fundamentals.data.eps_quarters || []).map((row, idx) => (
                        <tr key={idx} className="border-t border-white/5">
                          <td className="py-2">{row.quarter ?? "—"}</td>
                          <td>{formatRatio(row.eps_estimate)}</td>
                          <td>{formatRatio(row.eps_actual)}</td>
                          <td><YesNo value={row.beat} /></td>
                        </tr>
                      ))}
                      {(fundamentals.data.eps_quarters || []).length === 0 && <tr><td className="py-3 text-slate-400" colSpan={4}>Data unavailable</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </ChevronCard>

          <ChevronCard title="Coverage details" icon={<SectionIcon d="M12 17l-5 3 1.5-5.5L4 10h5.5L12 4l2.5 6H20l-4.5 4.5L17 20z" />} open={open.analysts} onToggle={() => setOpen((s) => ({ ...s, analysts: !s.analysts }))} loading={analysts.loading}>
            {analysts.loading && <Spinner />}
            {!analysts.loading && !analysts.available && <Unavailable />}
            {analysts.data && (
              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Metric label="Coverage stance" value={<span className={`rounded-full px-3 py-1 text-sm capitalize ${consensusClass(analysts.data.consensus)}`}>{analysts.data.consensus ?? "—"}</span>} />
                  <Metric label="Analysts covering" value={analysts.data.total_analysts ?? "—"} />
                  <PaywallLock locked={fieldLocked("targets")} minHeight="min-h-[4rem]">
                    <Metric label="Highest target" value={formatPrice(analysts.data.high_target)} />
                  </PaywallLock>
                  <PaywallLock locked={fieldLocked("targets")} minHeight="min-h-[4rem]">
                    <Metric label="Lowest target" value={formatPrice(analysts.data.low_target)} />
                  </PaywallLock>
                  <Metric label="EPS revisions" value={analysts.data.eps_revisions_trend ?? "Data unavailable"} className={sentimentClass(analysts.data.eps_revisions_trend)} />
                </div>
              </div>
            )}
          </ChevronCard>

          <ChevronCard title="Earnings" icon={<SectionIcon d="M8 7V3m8 4V3M4 11h16M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />} open={open.earnings} onToggle={() => setOpen((s) => ({ ...s, earnings: !s.earnings }))} loading={earnings.loading}>
            {earnings.loading && <Spinner />}
            {!earnings.loading && !earnings.available && <Unavailable />}
            {earnings.data && (
              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Metric label="Next earnings" value={earnings.data.next_earnings_date ?? "Data unavailable"} />
                  <Metric label="Days away" value={earnings.data.days_away ?? "—"} className={typeof earnings.data.days_away === "number" && earnings.data.days_away < 7 ? "text-amber-300" : ""} />
                  <Metric label="Time of day" value={earnings.data.time_of_day ?? "Data unavailable"} />
                  <Metric label="EPS consensus" value={formatRatio(earnings.data.eps_estimate)} />
                  <Metric label="EPS whisper" value={earnings.data.eps_whisper == null ? "Data unavailable" : formatRatio(earnings.data.eps_whisper)} />
                  <Metric label="Revenue estimate" value={formatCompact(earnings.data.revenue_estimate)} />
                  <Metric label="Avg historical move" value={pct(earnings.data.average_historical_move)} />
                  <Metric label="Implied move" value={pct(earnings.data.implied_move)} />
                  <Metric label="Volatility underpriced" value={<YesNo value={earnings.data.volatility_underpriced} />} />
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="text-slate-400">
                      <tr>
                        <th className="py-2">Quarter</th>
                        <th>EPS Est</th>
                        <th>EPS Actual</th>
                        <th>Beat?</th>
                        <th>Next-day move</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(earnings.data.results || []).map((row, idx) => (
                        <tr key={idx} className="border-t border-white/5">
                          <td className="py-2">{row.quarter ?? "—"}</td>
                          <td>{formatRatio(row.eps_estimate)}</td>
                          <td>{formatRatio(row.eps_actual)}</td>
                          <td><YesNo value={row.beat} /></td>
                          <td className={toneClass(row.next_day_move)}>{pct(row.next_day_move)}</td>
                        </tr>
                      ))}
                      {(earnings.data.results || []).length === 0 && <tr><td className="py-3 text-slate-400" colSpan={5}>Data unavailable</td></tr>}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </ChevronCard>

          <ChevronCard title="News & Sentiment" icon={<SectionIcon d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10l6 6v8a2 2 0 01-2 2z" />} open={open.sentiment} onToggle={() => setOpen((s) => ({ ...s, sentiment: !s.sentiment }))} loading={sentiment.loading}>
            {sentiment.loading && <Spinner />}
            {!sentiment.loading && !sentiment.available && <Unavailable />}
            {sentiment.data && (
              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Metric label="Sentiment score" value={sentiment.data.overall_score ?? "—"} className={scoreColor(sentiment.data.overall_score)} />
                  <Metric label="Reddit mentions" value={`${sentiment.data.reddit?.mention_count ?? "Data unavailable"} · ${sentiment.data.reddit?.trend ?? ""}`} className={sentimentClass(sentiment.data.reddit?.trend)} />
                  <Metric label="Google Trends" value={`${sentiment.data.google_trends?.score ?? "Data unavailable"} · ${sentiment.data.google_trends?.direction ?? ""}`} className={sentimentClass(sentiment.data.google_trends?.direction)} />
                  <Metric label="Positive vs negative (7d)" value={sentiment.data.positive_ratio == null ? "Data unavailable" : `${sentiment.data.positive_count}/${sentiment.data.negative_count}`} />
                </div>
                <div className="space-y-3">
                  {(sentiment.data.headlines || []).map((item, idx) => (
                    <div key={idx} className="rounded-xl bg-ink-900/70 px-4 py-3">
                      <p className="text-sm font-medium">{item.headline ?? "—"}</p>
                      <p className="mt-1 text-xs text-slate-400">
                        {item.source ?? "Unknown"} · <span className={sentimentClass(item.sentiment)}>{item.sentiment}</span> · {item.published_at ?? "—"}
                      </p>
                    </div>
                  ))}
                  {(sentiment.data.headlines || []).length === 0 && <Unavailable />}
                </div>
              </div>
            )}
          </ChevronCard>

          <ChevronCard title="Insider & Institutional" icon={<SectionIcon d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zm12 10v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />} open={open.ownership} onToggle={() => setOpen((s) => ({ ...s, ownership: !s.ownership }))} loading={ownership.loading}>
            {ownership.loading && <Spinner />}
            {!ownership.loading && !ownership.available && <Unavailable />}
            {ownership.data && (
              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Metric label="Net insider sentiment" value={ownership.data.net_insider_sentiment ?? "Data unavailable"} className={sentimentClass(ownership.data.net_insider_sentiment)} />
                  <Metric label="Institutional ownership" value={ownership.data.institutional_ownership_pct == null ? "Data unavailable" : isPlaceholder(ownership.data.institutional_ownership_pct) ? String(ownership.data.institutional_ownership_pct) : `${Number(ownership.data.institutional_ownership_pct).toFixed(1)}%`} />
                  <Metric label="Inst. change last quarter" value={ownership.data.institutional_ownership_change == null ? "Data unavailable" : pct(ownership.data.institutional_ownership_change as number)} className={toneClass(ownership.data.institutional_ownership_change as number)} />
                  <Metric label="Institutions adding" value={ownership.data.new_institutional_additions ?? ownership.data.new_institutional_buyers ?? "Data unavailable"} />
                  <Metric label="Short interest" value={ownership.data.short_interest_pct == null ? "Data unavailable" : isPlaceholder(ownership.data.short_interest_pct) ? String(ownership.data.short_interest_pct) : `${Number(ownership.data.short_interest_pct).toFixed(2)}%`} />
                  <Metric label="Short trend" value={ownership.data.short_interest_trend ?? "Data unavailable"} className={sentimentClass(ownership.data.short_interest_trend)} />
                  <Metric label="Days to cover" value={formatRatio(ownership.data.days_to_cover)} />
                </div>
                <PaywallLock locked={fieldLocked("insider_amounts")} minHeight="min-h-[10rem]">
                <div className="overflow-x-auto">
                  <p className="mb-2 text-sm font-medium">Insider transactions last 90 days</p>
                  <table className="w-full text-left text-sm">
                    <thead className="text-slate-400"><tr><th className="py-2">Name</th><th>Title</th><th>Action</th><th>Shares</th><th>Value</th><th>Date</th></tr></thead>
                    <tbody>
                      {(ownership.data.insider_transactions || []).map((row, idx) => (
                        <tr key={idx} className="border-t border-white/5">
                          <td className="py-2">{row.name ?? "—"}</td>
                          <td>{row.title ?? "—"}</td>
                          <td className={/dispos/i.test(publicAction(row.action)) ? "text-rose-400" : "text-gsr-accent"}>{publicAction(row.action)}</td>
                          <td>{formatCompact(row.shares)}</td>
                          <td>{formatCompact(row.value)}</td>
                          <td>{row.date ?? "—"}</td>
                        </tr>
                      ))}
                      {(ownership.data.insider_transactions || []).length === 0 && <tr><td className="py-3 text-slate-400" colSpan={6}>Data unavailable</td></tr>}
                    </tbody>
                  </table>
                </div>
                <div>
                  <p className="mb-2 text-sm font-medium">Top 3 holders</p>
                  {(ownership.data.top_holders || []).map((row, idx) => (
                    <p key={idx} className="text-sm text-slate-300">{row.holder} · {formatCompact(row.shares)} · change {row.change == null ? "Data unavailable" : isPlaceholder(row.change) ? String(row.change) : pct(row.change as number)}</p>
                  ))}
                  {(ownership.data.top_holders || []).length === 0 && <Unavailable />}
                </div>
                <div>
                  <p className="mb-2 text-sm font-medium">Congressional trades last 45 days</p>
                  {(ownership.data.congressional_trades || []).length === 0 && <p className="text-sm text-slate-400">None / Data unavailable</p>}
                  {(ownership.data.congressional_trades || []).map((row, idx) => (
                    <p key={idx} className="text-sm">{row.politician} · {publicAction(row.action)} · {row.amount} · {row.date}</p>
                  ))}
                </div>
                </PaywallLock>
              </div>
            )}
          </ChevronCard>

          {showDividends && (
            <ChevronCard title="Dividends" icon={<SectionIcon d="M12 8c-2.2 0-4 1.3-4 3s1.8 3 4 3 4 1.3 4 3-1.8 3-4 3m0-12V5m0 14v-1" />} open={open.dividends} onToggle={() => setOpen((s) => ({ ...s, dividends: !s.dividends }))} loading={dividends.loading}>
              {dividends.loading && <Spinner />}
              {!dividends.loading && !dividends.available && <Unavailable />}
              {dividends.data && (
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Metric label="Annual yield" value={dividends.data.annual_yield == null ? "—" : `${dividends.data.annual_yield.toFixed(2)}%`} />
                  <Metric label="Payout ratio" value={ratioPct(dividends.data.payout_ratio)} />
                  <Metric label="5y growth rate" value={dividends.data.growth_rate_5y == null ? "Data unavailable" : `${dividends.data.growth_rate_5y.toFixed(2)}%`} />
                  <Metric label="Next dividend date" value={dividends.data.next_dividend_date ?? "Data unavailable"} />
                </div>
              )}
            </ChevronCard>
          )}

          <ChevronCard title="Sector Comparison" icon={<SectionIcon d="M4 19h16M7 16l3-8 4 4 3-6" />} open={open.sector} onToggle={() => setOpen((s) => ({ ...s, sector: !s.sector }))} loading={sector.loading}>
            {sector.loading && <Spinner />}
            {!sector.loading && !sector.available && <Unavailable />}
            {sector.data && (
              <div className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <Metric label="Sector" value={`${sector.data.sector ?? "—"} (${sector.data.sector_etf ?? "—"})`} />
                  <Metric label="Sector momentum" value={sector.data.sector_momentum === "in" ? "Money flowing in" : sector.data.sector_momentum === "out" ? "Money flowing out" : "Data unavailable"} className={sentimentClass(sector.data.sector_momentum)} />
                  <Metric label="Rank within sector" value={sector.data.sector_rank == null ? "Data unavailable" : `${sector.data.sector_rank} of ${sector.data.peer_count ?? "—"}`} />
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead className="text-slate-400"><tr><th className="py-2">Window</th><th>Stock</th><th>Sector ETF</th><th>Relative</th></tr></thead>
                    <tbody>
                      {(["1m", "3m", "1y"] as const).map((window) => (
                        <tr key={window} className="border-t border-white/5">
                          <td className="py-2 uppercase">{window}</td>
                          <td className={toneClass(sector.data?.stock[window])}>{pct(sector.data?.stock[window])}</td>
                          <td className={toneClass(sector.data?.sector_etf_perf[window])}>{pct(sector.data?.sector_etf_perf[window])}</td>
                          <td className={toneClass(sector.data?.relative[window])}>{pct(sector.data?.relative[window])}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </ChevronCard>
        </div>
      )}
    </section>
  );
}

function AnalystConsensusCard({
  bullish,
  neutral,
  bearish,
  price,
  averageTarget,
  upsidePct,
  lockTargets,
}: {
  bullish: number | null | undefined;
  neutral: number | null | undefined;
  bearish: number | null | undefined;
  price: number | null | undefined;
  averageTarget: number | string | null | undefined;
  upsidePct: number | string | null | undefined;
  lockTargets: boolean;
}) {
  const bull = bullish ?? 0;
  const mid = neutral ?? 0;
  const bear = bearish ?? 0;
  const total = bull + mid + bear;
  return (
    <article className="glass-card rounded-2xl p-6 sm:p-7">
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-gsr-accent">Analyst consensus</p>
      <div className="mt-5 grid gap-6 lg:grid-cols-[1.2fr_0.8fr] lg:items-center">
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3 text-center">
            <div>
              <p className="text-3xl font-semibold text-gsr-accent">{bullish ?? "—"}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.14em] text-gsr-muted">Bullish</p>
            </div>
            <div>
              <p className="text-3xl font-semibold text-zinc-300">{neutral ?? "—"}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.14em] text-gsr-muted">Neutral</p>
            </div>
            <div>
              <p className="text-3xl font-semibold text-rose-400">{bearish ?? "—"}</p>
              <p className="mt-1 text-xs uppercase tracking-[0.14em] text-gsr-muted">Bearish</p>
            </div>
          </div>
          <div className="h-2.5 overflow-hidden rounded-full bg-black/40">
            {total > 0 ? (
              <div className="flex h-full">
                <div className="bg-gsr-accent" style={{ width: `${(bull / total) * 100}%` }} />
                <div className="bg-zinc-500" style={{ width: `${(mid / total) * 100}%` }} />
                <div className="bg-rose-500" style={{ width: `${(bear / total) * 100}%` }} />
              </div>
            ) : (
              <div className="h-full w-full bg-white/10" />
            )}
          </div>
          <PaywallLock locked={lockTargets} minHeight="min-h-[3rem]">
            <p className="text-sm text-gsr-muted">
              Average target {formatPrice(averageTarget)} vs last print {formatPrice(price)}
            </p>
          </PaywallLock>
        </div>
        <PaywallLock locked={lockTargets} minHeight="min-h-[8rem]">
          <div className="rounded-2xl border border-gsr-border bg-black/25 px-5 py-6 text-center">
            <p className="text-xs uppercase tracking-[0.16em] text-gsr-muted">Implied to mean target</p>
            <p className={`mt-2 text-5xl font-semibold ${toneClass(typeof upsidePct === "number" ? upsidePct : null)}`}>
              {isPlaceholder(upsidePct) ? String(upsidePct) : pct(typeof upsidePct === "number" ? upsidePct : null)}
            </p>
          </div>
        </PaywallLock>
      </div>
    </article>
  );
}

function RecentActionsFeed({ actions, lockTargets }: { actions: AnalystAction[]; lockTargets: boolean }) {
  return (
    <article className="glass-card rounded-2xl p-6 sm:p-7">
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-gsr-accent">Recent analyst actions</p>
      <div className="mt-4 divide-y divide-white/5">
        {actions.length === 0 && <p className="py-4 text-sm text-gsr-muted">No recent desk notes were published on this snapshot.</p>}
        {actions.map((row, idx) => (
          <div key={`${row.firm}-${row.date}-${idx}`} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div className="min-w-0">
              <p className="font-medium">
                {row.name || "Research desk"}
                <span className="text-gsr-muted"> · {row.firm || "Unknown firm"}</span>
              </p>
              <p className="mt-1 text-sm text-gsr-muted">
                <Stars value={row.stars} />
                <span className="ml-3">{row.outlook_label || "Coverage note"}</span>
              </p>
              <p className={`mt-1 text-sm text-gsr-muted ${lockTargets ? "paywall-blur" : ""}`}>
                  {formatPrice(row.previous_target)} → {formatPrice(row.new_target)}
                </p>
              </div>
            <div className="text-right text-sm">
                <p className={row.direction === "raised" ? "text-gsr-accent" : row.direction === "lowered" ? "text-amber-300" : "text-gsr-muted"}>
                  {row.direction === "raised" ? "Raised ✅" : row.direction === "lowered" ? "Lowered ⚠️" : row.direction ? "Unchanged" : "🔒"}
                </p>
                <p className="text-gsr-muted">{daysAgoLabel(row.days_ago)}</p>
              </div>
          </div>
        ))}
      </div>
      {lockTargets && (
        <div className="mt-4 flex justify-center">
          <UpgradeButton />
        </div>
      )}
    </article>
  );
}

function TopAnalystsList({ analysts, lockCase }: { analysts: TopAnalyst[]; lockCase: boolean }) {
  return (
    <article className="glass-card rounded-2xl p-6 sm:p-7">
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-gsr-accent">Top analysts covering</p>
      <div className="mt-4 grid gap-4 md:grid-cols-3">
        {analysts.length === 0 && <p className="text-sm text-gsr-muted">Coverage names were not published on this snapshot.</p>}
        {analysts.map((row) => (
          <div key={`${row.firm}-${row.name}`} className="rounded-xl border border-gsr-border bg-black/20 px-4 py-4">
            <p className="font-semibold">{row.name || "Research desk"}</p>
            <p className="text-sm text-gsr-muted">{row.firm || "Unknown firm"}</p>
            <p className="mt-2">
              <Stars value={row.stars} />
            </p>
            <PaywallLock locked={lockCase} minHeight="min-h-[7rem]">
              <p className="mt-3 text-sm text-gsr-muted">Historical accuracy</p>
              <p className="font-semibold">{row.accuracy_pct == null || isPlaceholder(row.accuracy_pct) ? "Not published" : `${Number(row.accuracy_pct).toFixed(0)}%`}</p>
              <p className="mt-3 text-sm text-gsr-muted">Current target</p>
              <p className="font-semibold">{formatPrice(row.current_target)}</p>
              <p className={`mt-2 text-sm font-medium ${outlookTone(row.sentiment)}`}>{row.sentiment || "Neutral"}</p>
              <p className="mt-1 text-xs text-gsr-muted">{daysAgoLabel(row.days_ago)}</p>
            </PaywallLock>
          </div>
        ))}
      </div>
    </article>
  );
}

