export function isPaidPlan(plan?: string | null) {
  return plan === "pro" || plan === "newsletter_pro" || plan === "premium";
}

export function hasNewsletter(plan?: string | null) {
  return isPaidPlan(plan);
}

export function researchHref(ticker: string) {
  return `/research?ticker=${encodeURIComponent(ticker.trim().toUpperCase())}`;
}

export function planLabel(plan?: string | null) {
  if (isPaidPlan(plan)) return "Premium";
  return "Free";
}
