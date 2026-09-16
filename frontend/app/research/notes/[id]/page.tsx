import { notFound } from "next/navigation";

import { apiGetSafe } from "@/lib/api";
import { formatDate, formatPrice } from "@/lib/format";
import type { ResearchNote } from "@/lib/types";

type PageProps = { params: Promise<{ id: string }> | { id: string } };

export default async function ResearchNotePage({ params }: PageProps) {
  const resolved = params instanceof Promise ? await params : params;
  const note = await apiGetSafe<ResearchNote | null>(`/api/v1/research/${resolved.id}`, null);
  if (!note) notFound();

  return (
    <article className="mx-auto max-w-3xl space-y-6">
      <p className="text-sm uppercase tracking-wide text-emerald-400">
        {note.ticker ?? "Market"} · {note.rating ?? "unrated"}
      </p>
      <h1 className="text-4xl font-semibold tracking-tight">{note.title}</h1>
      <p className="text-slate-400">{formatDate(note.published_at)}</p>
      {note.target_price && (
        <p className="rounded-xl border border-white/10 bg-ink-800/80 px-4 py-3 text-slate-200">
          Target price {formatPrice(note.target_price)}
        </p>
      )}
      <p className="text-lg text-slate-300">{note.summary}</p>
      <div className="whitespace-pre-wrap leading-7 text-slate-200">{note.body}</div>
    </article>
  );
}
