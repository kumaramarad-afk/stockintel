export function trackEvent(name: string, props?: Record<string, string | number | boolean>) {
  if (typeof window === "undefined") return;
  try {
    const plausible = (window as Window & { plausible?: (event: string, options?: { props?: Record<string, unknown> }) => void }).plausible;
    if (typeof plausible === "function") {
      plausible(name, props ? { props } : undefined);
    }
    const gtag = (window as Window & { gtag?: (...args: unknown[]) => void }).gtag;
    if (typeof gtag === "function") {
      gtag("event", name, props || {});
    }
  } catch {
    // Analytics must never break the page.
  }
}
