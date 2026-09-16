"use client";

import { useEffect, useState } from "react";

import { PublicReportView } from "@/components/research/PublicReportView";
import { useAuth } from "@/components/layout/AuthProvider";
import { apiUrl } from "@/lib/api";
import { Spinner } from "@/components/research/ui";

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
};

export function PublicReportLoader({
  ticker,
  initial,
}: {
  ticker: string;
  initial: ReportPayload;
}) {
  const { token, user, loading: authLoading } = useAuth();
  const [report, setReport] = useState(initial);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (authLoading) return;
    let cancelled = false;
    async function load() {
      setLoading(true);
      try {
        const response = await fetch(apiUrl(`/api/v1/research/public/${encodeURIComponent(ticker)}`), {
          cache: "no-store",
          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
          signal: AbortSignal.timeout(180_000),
        });
        if (!response.ok) return;
        const payload = (await response.json()) as ReportPayload;
        if (!cancelled) setReport(payload);
      } catch {
        // Keep SSR preview.
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
      {loading && <Spinner label="Refreshing report for your account…" />}
      <PublicReportView report={report} />
    </div>
  );
}
