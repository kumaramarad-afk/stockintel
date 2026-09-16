import { ResearchDirectory } from "@/components/research/ResearchDirectory";
import { apiGetSafe } from "@/lib/api";

const FALLBACK = [
  "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "BRK.B", "AVGO", "JPM",
  "LLY", "V", "UNH", "XOM", "MA", "COST", "HD", "PG", "JNJ", "ABBV",
  "NFLX", "CRM", "BAC", "AMD", "WMT", "KO", "PEP", "MRK", "ADBE", "TMO",
  "PLTR", "COIN", "SOFI", "RIVN", "NIO", "LCID", "HOOD", "GME", "AMC", "MSTR",
  "SMCI", "ARM", "UBER", "DIS", "BA", "INTC", "PYPL", "SQ", "SHOP", "SNOW",
];

type DirectoryResponse = {
  count: number;
  tickers: Array<{
    ticker: string;
    name?: string | null;
    one_line?: string | null;
    price?: number | null;
  }>;
};

export const metadata = {
  title: "Research Reports — Browse 50+ Tickers | GetStockReport",
  description: "Browse research reports with bull case, bear case, and what has to be true — no buy/sell verdict.",
};

export default async function ResearchDirectoryPage() {
  const payload = await apiGetSafe<DirectoryResponse>("/api/v1/research/tickers", {
    count: FALLBACK.length,
    tickers: FALLBACK.map((ticker) => ({ ticker })),
  });
  const tickers = [...payload.tickers].sort((a, b) => a.ticker.localeCompare(b.ticker));
  const countLabel = `${Math.max(tickers.length, 50)}+ reports available`;
  return <ResearchDirectory tickers={tickers} countLabel={countLabel} />;
}
