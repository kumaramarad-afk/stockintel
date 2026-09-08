export const RESEARCH_PATH = "/research";

const AUTH_PAGES = new Set(["/login", "/register", "/auth/callback"]);

export function postLoginPath(path?: string | null): string {
  const raw = (path || RESEARCH_PATH).trim() || RESEARCH_PATH;
  const pathname = raw.split("?")[0];
  if (!pathname.startsWith("/") || pathname.startsWith("//")) return RESEARCH_PATH;
  if (AUTH_PAGES.has(pathname) || pathname.startsWith("/auth/")) return RESEARCH_PATH;
  if (pathname === "/") return RESEARCH_PATH;
  return raw.startsWith("/") ? raw : RESEARCH_PATH;
}

export function goToResearch(): void {
  window.location.assign(RESEARCH_PATH);
}
