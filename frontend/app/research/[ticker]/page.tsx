import type { Metadata } from "next";
import { notFound } from "next/navigation";

import { PublicReportLoader } from "@/components/research/PublicReportLoader";
import { apiGetSafe } from "@/lib/api";

const TICKER_RE = /^[A-Z][A-Z0-9.\-]{0,15}$/;

type PublicReport = {
  ticker: string;
  name?: string | null;
  price?: number | null;
  as_of?: string | null;
  one_line?: string | null;
  sections?: Record<string, string> | null;
  blurred_sections?: Record<string, string> | null;
  locked_sections?: string[];
  preview?: boolean;
  available?: boolean;
};

type PageProps = { params: Promise<{ ticker: string }> | { ticker: string } };

async function resolveParams(params: PageProps["params"]) {
  return params instanceof Promise ? await params : params;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { ticker: raw } = await resolveParams(params);
  const ticker = raw.trim().toUpperCase();
  const report = await apiGetSafe<PublicReport | null>(`/api/v1/research/public/${encodeURIComponent(ticker)}`, null);
  const oneLine =
    report?.one_line ||
    report?.sections?.one_line ||
    `${ticker} research report with bull case, bear case, and valuation context.`;
  const title = `${ticker} Research Report — Bull Case, Bear Case, What Has To Be True | GetStockReport`;
  const url = `https://getstockreport.com/research/${encodeURIComponent(ticker)}`;
  return {
    title,
    description: oneLine.slice(0, 160),
    alternates: { canonical: url },
    openGraph: {
      title: `${ticker} Analysis | GetStockReport`,
      description: oneLine.slice(0, 200),
      url,
      siteName: "GetStockReport",
      type: "article",
      images: [{ url: "/og-image.svg" }],
    },
    twitter: {
      card: "summary_large_image",
      title: `${ticker} Analysis`,
      description: oneLine.slice(0, 200),
      images: ["https://getstockreport.com/og-image.svg"],
    },
  };
}

export default async function ResearchTickerPage({ params }: PageProps) {
  const { ticker: raw } = await resolveParams(params);
  const ticker = raw.trim().toUpperCase();
  if (!TICKER_RE.test(ticker)) notFound();
  const report = await apiGetSafe<PublicReport | null>(`/api/v1/research/public/${encodeURIComponent(ticker)}`, {
    ticker,
    name: ticker,
    one_line: `Loading the research note for ${ticker}…`,
    sections: {
      one_line: `Loading the research note for ${ticker}…`,
      paying: "Pulling valuation context…",
      non_verdict:
        "It doesn't tell you to buy or sell. It won't, ever.\n\nYou have the valuation in context, the strongest version of both cases, and the specific assumptions the current price depends on.",
    },
    locked_sections: ["bulls", "bears", "assumptions", "watch"],
    preview: true,
    available: true,
  });
  return <PublicReportLoader ticker={ticker} initial={report} />;
}
