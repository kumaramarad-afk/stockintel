import type { MetadataRoute } from "next";

import { apiGetSafe } from "@/lib/api";

const FALLBACK = [
  "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "AVGO", "JPM",
  "LLY", "V", "UNH", "XOM", "MA", "COST", "HD", "PG", "JNJ", "ABBV",
  "NFLX", "CRM", "BAC", "AMD", "WMT", "KO", "PEP", "MRK", "ADBE", "TMO",
  "PLTR", "COIN", "SOFI", "RIVN", "NIO", "LCID", "HOOD", "GME", "AMC", "MSTR",
  "SMCI", "ARM", "UBER", "DIS", "BA", "INTC", "PYPL", "SQ", "SHOP", "SNOW",
];

type DirectoryResponse = {
  tickers: Array<{ ticker: string; generated_at?: string | null }>;
};

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const base = "https://getstockreport.com";
  const directory = await apiGetSafe<DirectoryResponse>("/api/v1/research/tickers", {
    tickers: FALLBACK.map((ticker) => ({ ticker })),
  });
  const tickers = directory.tickers.length ? directory.tickers : FALLBACK.map((ticker) => ({ ticker }));
  const now = new Date();
  return [
    { url: `${base}/`, lastModified: now, changeFrequency: "weekly", priority: 1 },
    { url: `${base}/research`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${base}/newsletter`, lastModified: now, changeFrequency: "weekly", priority: 0.6 },
    { url: `${base}/subscribe`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    ...tickers.map((row) => ({
      url: `${base}/research/${encodeURIComponent(row.ticker)}`,
      lastModified: row.generated_at ? new Date(row.generated_at) : now,
      changeFrequency: "weekly" as const,
      priority: 0.8,
    })),
  ];
}
