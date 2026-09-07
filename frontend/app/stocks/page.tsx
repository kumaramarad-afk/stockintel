import Link from "next/link";

import { apiGetSafe } from "@/lib/api";
import { formatChange, formatPrice } from "@/lib/format";
import type { Stock } from "@/lib/types";

export default async function StocksPage() {
  const stocks = await apiGetSafe<Stock[]>("/api/v1/stocks", []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Stocks</h1>
        <p className="mt-2 text-slate-300">Coverage universe and latest snapshots.</p>
      </div>
      <div className="overflow-hidden rounded-2xl border border-white/10 bg-ink-800/80">
        <table className="w-full text-left text-sm">
          <thead className="bg-ink-900/80 text-slate-400">
            <tr>
              <th className="px-4 py-3 font-medium">Ticker</th>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Sector</th>
              <th className="px-4 py-3 font-medium">Price</th>
              <th className="px-4 py-3 font-medium">Change</th>
            </tr>
          </thead>
          <tbody>
            {stocks.map((stock) => {
              const change = formatChange(stock.latest_price?.change_percent);
              return (
                <tr key={stock.id} className="border-t border-white/5 hover:bg-ink-700/70">
                  <td className="px-4 py-3 font-medium">
                    <Link href={`/stocks/${stock.ticker}`} className="text-emerald-400 hover:text-emerald-300">
                      {stock.ticker}
                    </Link>
                  </td>
                  <td className="px-4 py-3">{stock.name}</td>
                  <td className="px-4 py-3 text-slate-300">{stock.sector ?? "—"}</td>
                  <td className="px-4 py-3">{formatPrice(stock.latest_price?.price)}</td>
                  <td className={`px-4 py-3 ${change.positive ? "text-emerald-400" : "text-rose-400"}`}>
                    {change.label}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {stocks.length === 0 && <p className="px-4 py-8 text-sm text-slate-400">No stocks found.</p>}
      </div>
    </div>
  );
}
