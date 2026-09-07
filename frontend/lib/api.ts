function normalizeApiOrigin(raw: string | undefined | null, fallback = ""): string {
  let base = (raw || "").trim().replace(/\/+$/, "");
  // Env is often set to https://host/api while every client path already starts with /api/v1.
  if (base.toLowerCase().endsWith("/api")) {
    base = base.slice(0, -4);
  }
  return base || fallback;
}

export function publicApiBase(): string {
  const fallback = process.env.NODE_ENV === "production" ? "" : "http://localhost:8000";
  return normalizeApiOrigin(process.env.NEXT_PUBLIC_API_URL, fallback);
}

export function serverApiBase(): string {
  return normalizeApiOrigin(
    process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL,
    "http://localhost:8000",
  );
}

export function apiUrl(path: string): string {
  const suffix = path.startsWith("/") ? path : `/${path}`;
  return `${publicApiBase()}${suffix}`;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${serverApiBase()}${path}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`API ${response.status} for ${path}`);
  }
  return response.json() as Promise<T>;
}

export async function apiGetSafe<T>(path: string, fallback: T): Promise<T> {
  try {
    return await apiGet<T>(path);
  } catch {
    return fallback;
  }
}

export async function apiPost<T>(path: string, body: unknown, timeoutMs = 120_000): Promise<T> {
  const response = await fetch(`${serverApiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
    signal: AbortSignal.timeout(timeoutMs),
  });
  if (!response.ok) {
    let detail = `API ${response.status} for ${path}`;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
      else if (Array.isArray(payload.detail) && payload.detail[0]?.msg) detail = String(payload.detail[0].msg);
    } catch {
      // Keep the status fallback when the body is not JSON.
    }
    throw new Error(detail);
  }
  return response.json() as Promise<T>;
}
