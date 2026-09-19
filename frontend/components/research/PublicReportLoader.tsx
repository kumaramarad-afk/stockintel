"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { LoadingProgressBar } from "@/components/LoadingProgressBar";
import { ReportSkeleton } from "@/components/ReportSkeleton";
import { PublicReportView } from "@/components/research/PublicReportView";
import { useAuth } from "@/components/layout/AuthProvider";
import { apiUrl } from "@/lib/api";

type ReportPayload = {
  ticker: string;
  name?: string | null;
  price?: number | null;
  as_of?: string | null;
  one_line?: string | null;
  sections?: Record<string, string> | null;
  blurred_sections?: Record<string, string> | null;
  locked_sections?: string[];
  preview?: boolean;
  data_sections?: Record<string, unknown> | null;
  available?: boolean;
  error?: string | null;
};

export function PublicReportLoader({
  ticker,
  initial,
}: {
  ticker: string;
  initial: ReportPayload;
}) {
  const router = useRouter();
  const { token, user, loading: authLoading } = useAuth();
  const [report, setReport] = useState(initial);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(apiUrl(`/api/v1/research/public/${encodeURIComponent(ticker)}`), {
          cache: "no-store",
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          signal: AbortSignal.timeout(180_000),
        });
        if (!response.ok) {
          throw new Error(response.status === 404 ? `Report not found for ${ticker}.` : `Failed to load report (${response.status}).`);
        }
        const payload = (await response.json()) as ReportPayload;
        if (payload.available === false || payload.error) {
          throw new Error(payload.error || `Report not found for ${ticker}.`);
        }
        if (!cancelled) setReport(payload);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : `Report not found for ${ticker}. Try another stock.`);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [ticker, token, user?.plan, authLoading]);

  return (
    <div className="space-y-4">
      <LoadingProgressBar isLoading={loading || authLoading} />
      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 px-6 py-10 text-center">
          <p className="text-base font-semibold text-rose-800">Report not found for {ticker}. Try another stock.</p>
          <p className="mt-2 text-sm text-rose-700">{error}</p>
          <button
            type="button"
            onClick={() => router.push("/research")}
            className="mt-5 rounded-xl bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
          >
            Back to research
          </button>
        </div>
      ) : loading && !report.sections?.paying ? (
        <ReportSkeleton />
      ) : (
        <>
          {loading ? <p className="text-sm text-slate-500">Loading report…</p> : null}
          <PublicReportView report={report} />
        </>
      )}
    </div>
  );
}
