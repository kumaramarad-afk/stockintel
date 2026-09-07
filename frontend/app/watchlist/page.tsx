import Link from "next/link";

import { apiGetSafe } from "@/lib/api";
import type { Watchlist } from "@/lib/types";

export default async function WatchlistPage() {
  const watchlists = await apiGetSafe<Watchlist[]>("/api/v1/watchlists", []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold">Watchlist</h1>
        <p className="mt-2 text-slate-300">Saved coverage lists for the research desk.</p>
      </div>
      {watchlists.map((watchlist) => (
        <section key={watchlist.id} className="rounded-2xl border border-white/10 bg-ink-800/80 p-6">
          <h2 className="text-lg font-semibold">{watchlist.name}</h2>
          <div className="mt-4 divide-y divide-white/5">
            {watchlist.items.map((item) => (
              <div key={item.id} className="flex items-center justify-between py-3">
                <Link href={`/stocks/${item.ticker}`} className="font-medium text-emerald-400 hover:text-emerald-300">
                  {item.ticker}
                </Link>
                <span className="text-sm text-slate-300">{item.name}</span>
              </div>
            ))}
            {watchlist.items.length === 0 && <p className="py-3 text-sm text-slate-400">Empty list.</p>}
          </div>
        </section>
      ))}
      {watchlists.length === 0 && <p className="text-sm text-slate-400">No watchlists yet.</p>}
    </div>
  );
}
