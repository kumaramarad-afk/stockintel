export function isPaidPlan(plan?: string | null) {
  return plan === "pro" || plan === "newsletter_pro";
}

export function hasNewsletter(plan?: string | null) {
  return plan === "newsletter_pro";
}

export function researchHref(ticker: string) {
  return `/research?ticker=${encodeURIComponent(ticker.trim().toUpperCase())}`;
}

export function planLabel(plan?: string | null) {
  if (plan === "newsletter_pro") return "Newsletter Pro";
  if (plan === "pro") return "Pro";
  return "Free";
}
