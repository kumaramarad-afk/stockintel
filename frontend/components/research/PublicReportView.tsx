"use client";

import Link from "next/link";
import type { ComponentProps } from "react";

import { ResearchMarkdown } from "@/components/research/ResearchMarkdown";
import { ReportDataSections } from "@/components/research/ReportDataSections";
import { useAuth } from "@/components/layout/AuthProvider";
import { trackEvent } from "@/lib/analytics";
import { formatPrice } from "@/lib/format";

type DataSections = NonNullable<ComponentProps<typeof ReportDataSections>["data"]>;

type ReportPayload = {
  ticker: string;
  name?: string | null;
  price?: number | null;
  as_of?: string | null;
  one_line?: string | null;
  sections?: {
    title?: string;
    one_line?: string;
    paying?: string;
    bulls?: string;
    bears?: string;
    assumptions?: string;
    watch?: string;
    non_verdict?: string;
    disclaimer?: string;
  } | null;
  blurred_sections?: {
    bulls?: string;
    bears?: string;
    assumptions?: string;
    watch?: string;
  } | null;
  locked_sections?: string[];
  preview?: boolean;
  data_sections?: DataSections | null;
};

function LockedSection({
  title,
  body,
  onSignup,
  onUpgrade,
}: {
  title: string;
  body: string;
  onSignup: () => void;
  onUpgrade: () => void;
}) {
  return (
    <div className="relative my-8 overflow-hidden rounded-2xl border border-slate-200">
      <div className="pointer-events-none select-none px-5 py-4 blur-[3px] opacity-50">
        <h2 className="text-xl font-semibold text-emerald-900">{title}</h2>
        <div className="mt-3 max-h-48 overflow-hidden">
          <ResearchMarkdown markdown={body || "Locked analysis content placeholder.\n\n- Point one\n- Point two\n- Point three"} />
        </div>
      </div>
      <div className="absolute inset-0 flex flex-col items-center justify-center bg-white/80 px-6 text-center">
        <p className="text-base font-semibold text-slate-900">Sign up free to read the full analysis</p>
        <p className="mt-1 max-w-sm text-sm text-slate-600">Bull case, bear case, assumptions, and what to watch next.</p>
        <div className="mt-4 flex flex-wrap justify-center gap-2">
          <button
            type="button"
            onClick={() => {
              trackEvent("signup_from_report");
              onSignup();
            }}
            className="rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
          >
            Sign up free
          </button>
          <button
            type="button"
            onClick={() => {
              trackEvent("upgrade_from_report");
              onUpgrade();
            }}
            className="rounded-xl border border-slate-300 bg-white px-4 py-2 text-sm font-semibold text-slate-800 hover:border-emerald-500"
          >
            Upgrade to Premium
          </button>
        </div>
      </div>
    </div>
  );
}

export function PublicReportView({ report }: { report: ReportPayload }) {
  const { user, openAuthModal, startCheckout } = useAuth();
  const sections = report.sections || {};
  const blurred = report.blurred_sections || {};
  const locked = new Set(report.locked_sections || []);
  const oneLine = sections.one_line || report.one_line || "";

  return (
    <article className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3 rounded-2xl border border-slate-200 bg-white px-5 py-4 shadow-sm">
        <div>
          <p className="text-xs tracking-[0.18em] text-slate-500">RESEARCH REPORT</p>
          <h1 className="mt-1 text-3xl font-semibold text-slate-900">{report.name || report.ticker}</h1>
          <p className="text-sm text-slate-500">{report.ticker}</p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-semibold text-slate-900">{formatPrice(report.price ?? null)}</p>
          {report.as_of && <p className="text-xs text-slate-500">As of {report.as_of}</p>}
        </div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white px-5 py-6 shadow-sm sm:px-8 sm:py-8">
        <p className="text-sm italic text-slate-500">
          Research note{report.as_of ? ` — ${report.as_of}` : ""}. Educational analysis, not financial advice.
        </p>
        <hr className="my-6 border-slate-200" />
        <h2 className="text-xl font-semibold text-emerald-900">The one-line version</h2>
        <p className="mt-3 text-[15px] leading-7 text-slate-800">{oneLine}</p>
        <p className="mt-3 text-[15px] leading-7 text-slate-600">That&apos;s the tension. Everything below is the detail.</p>
        <hr className="my-6 border-slate-200" />
        <h2 className="text-xl font-semibold text-emerald-900">1. What you&apos;re paying</h2>
        <div className="mt-3">
          <ResearchMarkdown markdown={sections.paying || "Valuation detail is loading."} />
        </div>

        {locked.has("bulls") ? (
          <LockedSection
            title="2. What the bulls are counting on"
            body={blurred.bulls || ""}
            onSignup={openAuthModal}
            onUpgrade={() => {
              if (!user) openAuthModal();
              else void startCheckout();
            }}
          />
        ) : (
          <>
            <hr className="my-6 border-slate-200" />
            <h2 className="text-xl font-semibold text-emerald-900">2. What the bulls are counting on</h2>
            <div className="mt-3">
              <ResearchMarkdown markdown={sections.bulls || ""} />
            </div>
          </>
        )}

        {locked.has("bears") ? (
          <LockedSection
            title="3. What the bears see"
            body={blurred.bears || ""}
            onSignup={openAuthModal}
            onUpgrade={() => {
              if (!user) openAuthModal();
              else void startCheckout();
            }}
          />
        ) : (
          <>
            <hr className="my-6 border-slate-200" />
            <h2 className="text-xl font-semibold text-emerald-900">3. What the bears see</h2>
            <div className="mt-3">
              <ResearchMarkdown markdown={sections.bears || ""} />
            </div>
          </>
        )}

        {locked.has("assumptions") ? (
          <LockedSection
            title="4. What would have to be true"
            body={blurred.assumptions || ""}
            onSignup={openAuthModal}
            onUpgrade={() => {
              if (!user) openAuthModal();
              else void startCheckout();
            }}
          />
        ) : (
          <>
            <hr className="my-6 border-slate-200" />
            <h2 className="text-xl font-semibold text-emerald-900">4. What would have to be true</h2>
            <div className="mt-3">
              <ResearchMarkdown markdown={sections.assumptions || ""} />
            </div>
          </>
        )}

        {locked.has("watch") ? (
          <LockedSection
            title="5. What to watch next"
            body={blurred.watch || ""}
            onSignup={openAuthModal}
            onUpgrade={() => {
              if (!user) openAuthModal();
              else void startCheckout();
            }}
          />
        ) : (
          <>
            <hr className="my-6 border-slate-200" />
            <h2 className="text-xl font-semibold text-emerald-900">5. What to watch next</h2>
            <div className="mt-3">
              <ResearchMarkdown markdown={sections.watch || ""} />
            </div>
          </>
        )}

        <hr className="my-6 border-slate-200" />
        <h2 className="text-xl font-semibold text-emerald-900">6. What this note does not do</h2>
        <div className="mt-3">
          <ResearchMarkdown
            markdown={
              sections.non_verdict ||
              "It doesn't tell you to buy or sell. It won't, ever.\n\nYou have the valuation in context, the strongest version of both cases, and the specific assumptions the current price depends on."
            }
          />
        </div>
        {sections.disclaimer && (
          <p className="mt-8 text-xs leading-5 text-slate-400">
            <ResearchMarkdown markdown={sections.disclaimer} />
          </p>
        )}

        <ReportDataSections ticker={report.ticker} data={report.data_sections} />
      </div>

      <p className="text-sm text-slate-500">
        <Link href="/research" className="text-emerald-400 hover:text-emerald-300">
          ← Browse all reports
        </Link>
      </p>
    </article>
  );
}
