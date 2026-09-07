const API_URL =
  process.env.INTERNAL_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { cache: "no-store" });
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
  const response = await fetch(`${API_URL}${path}`, {
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
