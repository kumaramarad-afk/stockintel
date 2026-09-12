import Link from "next/link";
import { notFound } from "next/navigation";

import { apiGetSafe } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { researchHref } from "@/lib/plans";
import type { NewsletterIssue } from "@/lib/types";

export default async function NewsletterIssuePage({ params }: { params: { id: string } }) {
  const issue = await apiGetSafe<NewsletterIssue | null>(`/api/v1/newsletters/issues/${params.id}`, null);
  if (!issue) notFound();
  const ticker = issue.ticker?.trim().toUpperCase();

  return (
    <article className="mx-auto max-w-3xl space-y-5">
      <p className="text-sm uppercase tracking-wide text-gsr-accent">Newsletter</p>
      <h1 className="text-4xl font-semibold tracking-tight">{issue.title}</h1>
      <p className="text-gsr-muted">{formatDate(issue.published_at)}</p>
      {ticker && (
        <Link
          href={researchHref(ticker)}
          className="inline-flex rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-emerald-400"
        >
          Open {ticker} research report
        </Link>
      )}
      <p className="text-lg text-white/80">{issue.excerpt}</p>
      {issue.body.trim().startsWith("<") ? (
        <div className="leading-7 text-white/80" dangerouslySetInnerHTML={{ __html: issue.body }} />
      ) : (
        <div className="whitespace-pre-wrap leading-7 text-white/80">{issue.body}</div>
      )}
    </article>
  );
}
