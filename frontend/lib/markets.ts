import { apiUrl } from "@/lib/api";

export type MarketQuote = {
  symbol: string;
  name: string;
  price: number | null;
  previous_close?: number | null;
  change_percent: number | null;
};

export const INDEX_SYMBOLS = ["^GSPC", "^IXIC", "^DJI"] as const;
export const POPULAR_SYMBOLS = ["AAPL", "NVDA", "MSFT"] as const;

export async function fetchMarketQuotes(symbols: readonly string[]): Promise<MarketQuote[]> {
  const path = `/api/v1/markets/quotes?symbols=${encodeURIComponent(symbols.join(","))}`;
  const urls = [path, apiUrl(path)];
  let lastError: Error | null = null;
  for (const url of urls) {
    try {
      const response = await fetch(url, { cache: "no-store" });
      if (!response.ok) {
        lastError = new Error("Could not load market quotes");
        continue;
      }
      return response.json() as Promise<MarketQuote[]>;
    } catch (err) {
      lastError = err instanceof Error ? err : new Error("Could not load market quotes");
    }
  }
  throw lastError || new Error("Could not load market quotes");
}

export function formatTapePrice(value: number | null | undefined) {
  if (value == null) return "—";
  return value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export function formatTapePercent(value: number | null | undefined) {
  if (value == null) return "—";
  const positive = value >= 0;
  return `${positive ? "+" : ""}${value.toFixed(2)}%`;
}
