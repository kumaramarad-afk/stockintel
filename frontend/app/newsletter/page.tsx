import { NewsletterDesk } from "@/components/newsletter/NewsletterDesk";
import { apiGetSafe } from "@/lib/api";
import type { Newsletter, NewsletterIssue } from "@/lib/types";

export default async function NewsletterPage() {
  const [newsletters, issues] = await Promise.all([
    apiGetSafe<Newsletter[]>("/api/v1/newsletters", []),
    apiGetSafe<NewsletterIssue[]>("/api/v1/newsletters/weekly/issues", []),
  ]);
  const primary = newsletters.find((item) => item.slug === "weekly") ?? newsletters[0];

  return (
    <NewsletterDesk
      weeklyName={primary?.name ?? "GetStockReport Weekly"}
      weeklyDescription={primary?.description ?? "Market, research, and earnings briefing."}
      weeklySlug={primary?.slug ?? "weekly"}
      issues={issues}
    />
  );
}
