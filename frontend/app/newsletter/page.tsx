import Link from "next/link";

import { SubscribeForm } from "@/components/newsletter/SubscribeForm";
import { apiGetSafe } from "@/lib/api";
import { formatDate } from "@/lib/format";
import type { Newsletter, NewsletterIssue } from "@/lib/types";

export default async function NewsletterPage() {
  const [newsletters, issues] = await Promise.all([
    apiGetSafe<Newsletter[]>("/api/v1/newsletters", []),
    apiGetSafe<NewsletterIssue[]>("/api/v1/newsletters/weekly/issues", []),
  ]);
  const primary = newsletters[0];

  return (
    <div className="space-y-8">
      <section className="glass-card rounded-2xl p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.28em] text-gsr-accent">Newsletter</p>
        <h1 className="mt-3 text-3xl font-semibold">{primary?.name ?? "GetStockReport Weekly"}</h1>
        <p className="mt-2 max-w-2xl text-gsr-muted">
          {primary?.description ?? "Market, research, and earnings briefing."}
        </p>
        <SubscribeForm slug={primary?.slug ?? "weekly"} />
      </section>

      <section className="space-y-4">
        <h2 className="text-xl font-semibold">Archive</h2>
        {issues.map((issue) => (
          <Link
            key={issue.id}
            href={`/newsletter/${issue.id}`}
            className="glass-card block rounded-2xl p-6 transition hover:border-gsr-accent/30"
          >
            <p className="text-sm text-gsr-muted">{formatDate(issue.published_at)}</p>
            <h3 className="mt-1 text-lg font-semibold">{issue.title}</h3>
            <p className="mt-2 text-gsr-muted">{issue.excerpt}</p>
          </Link>
        ))}
        {issues.length === 0 && <p className="text-sm text-gsr-muted">No issues yet.</p>}
      </section>
    </div>
  );
}
