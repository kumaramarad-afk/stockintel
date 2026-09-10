"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { apiUrl } from "@/lib/api";
import { postLoginPath } from "@/lib/auth";
import { clearToken, readToken, writeToken } from "@/lib/session";

export type Account = {
  id: string;
  email: string;
  full_name: string;
  plan: string;
  subscribed_at: string | null;
  created_at: string;
  is_active: boolean;
  reports_used?: number;
  reports_limit?: number;
  reports_generated?: number;
  reports_remaining?: number;
  oauth_provider?: string | null;
};

type AuthContextValue = {
  user: Account | null;
  token: string | null;
  loading: boolean;
  authModalOpen: boolean;
  openAuthModal: () => void;
  closeAuthModal: () => void;
  login: (email: string, password: string) => Promise<void>;
  register: (fullName: string, email: string, password: string) => Promise<void>;
  subscribe: (plan?: "pro" | "free") => Promise<void>;
  startCheckout: () => Promise<void>;
  startBillingPortal: () => Promise<void>;
  startOAuth: (provider: "google" | "apple") => void;
  applyToken: (value: string) => Promise<void>;
  refreshProfile: () => Promise<void>;
  verifyCheckoutSession: (sessionId?: string | null) => Promise<Account>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

async function parseError(response: Response) {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") return payload.detail;
  } catch {
    // ignore
  }
  return `Request failed (${response.status})`;
}

async function fetchProfile(value: string): Promise<Account> {
  const headers = { Authorization: `Bearer ${value}` };
  const paths = ["/api/v1/auth/me", "/api/v1/users/me"];
  let lastError: Error | null = null;
  for (const path of paths) {
    try {
      const response = await fetch(apiUrl(path), { headers, cache: "no-store" });
      if (response.status === 401 || response.status === 403) {
        throw new Error("Invalid or expired session");
      }
      if (!response.ok) {
        lastError = new Error(await parseError(response));
        continue;
      }
      return (await response.json()) as Account;
    } catch (err) {
      if (err instanceof Error && err.message === "Invalid or expired session") throw err;
      lastError = err instanceof Error ? err : new Error("Could not load account");
    }
  }
  throw lastError || new Error("Could not load account");
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  const refresh = useCallback(async (value: string) => {
    try {
      const account = await fetchProfile(value);
      writeToken(value);
      setToken(value);
      setUser(account);
    } catch (err) {
      if (err instanceof Error && err.message === "Invalid or expired session") {
        clearToken();
        setToken(null);
        setUser(null);
        return;
      }
      writeToken(value);
      setToken(value);
    }
  }, []);

  useEffect(() => {
    const stored = readToken();
    if (!stored) {
      setLoading(false);
      return;
    }
    setToken(stored);
    writeToken(stored);
    refresh(stored).finally(() => setLoading(false));
  }, [refresh]);

  const applySession = (accessToken: string, account: Account) => {
    writeToken(accessToken);
    setToken(accessToken);
    setUser(account);
  };

  const applyToken = useCallback(async (value: string) => {
    writeToken(value);
    setToken(value);
    await refresh(value);
    if (!readToken()) throw new Error("Invalid or expired session");
  }, [refresh]);

  const refreshProfile = useCallback(async () => {
    const value = token || readToken();
    if (!value) return;
    await refresh(value);
  }, [refresh, token]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await fetch(apiUrl("/api/v1/users/login"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) throw new Error(await parseError(response));
    const payload = (await response.json()) as { access_token: string; user: Account };
    applySession(payload.access_token, payload.user);
  }, []);

  const register = useCallback(async (fullName: string, email: string, password: string) => {
    const response = await fetch(apiUrl("/api/v1/users/register"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name: fullName, email, password }),
    });
    if (!response.ok) throw new Error(await parseError(response));
    const payload = (await response.json()) as { access_token: string; user: Account };
    applySession(payload.access_token, payload.user);
  }, []);

  const subscribe = useCallback(async (plan: "pro" | "free" = "pro") => {
    if (!token) throw new Error("Sign in to subscribe");
    const response = await fetch(apiUrl("/api/v1/users/subscribe"), {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({ plan }),
    });
    if (!response.ok) throw new Error(await parseError(response));
    setUser((await response.json()) as Account);
  }, [token]);

  const startCheckout = useCallback(async () => {
    if (!token) {
      setAuthModalOpen(true);
      return;
    }
    const response = await fetch(apiUrl("/api/checkout"), {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error(await parseError(response));
    const payload = (await response.json()) as { url: string };
    window.location.href = payload.url;
  }, [token]);

  const startBillingPortal = useCallback(async () => {
    if (!token) {
      setAuthModalOpen(true);
      return;
    }
    const response = await fetch(apiUrl("/api/billing/portal"), {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error(await parseError(response));
    const payload = (await response.json()) as { url: string };
    window.location.href = payload.url;
  }, [token]);

  const verifyCheckoutSession = useCallback(async (sessionId?: string | null) => {
    const value = token || readToken();
    if (!value) throw new Error("Sign in to verify payment");
    const response = await fetch(apiUrl("/api/v1/payments/verify-session"), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${value}`,
      },
      body: JSON.stringify({ session_id: sessionId || undefined }),
      cache: "no-store",
    });
    if (!response.ok) throw new Error(await parseError(response));
    const account = (await response.json()) as Account;
    setUser(account);
    return account;
  }, [token]);

  const startOAuth = useCallback((provider: "google" | "apple") => {
    const next = postLoginPath(window.location.pathname + window.location.search);
    window.location.href = apiUrl(`/api/v1/auth/${provider}/start?next=${encodeURIComponent(next)}`);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    setToken(null);
    setUser(null);
  }, []);

  const openAuthModal = useCallback(() => setAuthModalOpen(true), []);
  const closeAuthModal = useCallback(() => setAuthModalOpen(false), []);

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      authModalOpen,
      openAuthModal,
      closeAuthModal,
      login,
      register,
      subscribe,
      startCheckout,
      startBillingPortal,
      startOAuth,
      applyToken,
      refreshProfile,
      verifyCheckoutSession,
      logout,
    }),
    [
      user,
      token,
      loading,
      authModalOpen,
      openAuthModal,
      closeAuthModal,
      login,
      register,
      subscribe,
      startCheckout,
      startBillingPortal,
      startOAuth,
      applyToken,
      refreshProfile,
      verifyCheckoutSession,
      logout,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
