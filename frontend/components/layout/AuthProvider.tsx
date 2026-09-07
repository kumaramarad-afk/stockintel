"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const TOKEN_KEY = "gsr_token";

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
  startOAuth: (provider: "google" | "apple") => void;
  applyToken: (value: string) => Promise<void>;
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

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  const refresh = useCallback(async (value: string) => {
    const response = await fetch(`${API_URL}/api/v1/users/me`, {
      headers: { Authorization: `Bearer ${value}` },
      cache: "no-store",
    });
    if (!response.ok) {
      localStorage.removeItem(TOKEN_KEY);
      setToken(null);
      setUser(null);
      return;
    }
    setUser((await response.json()) as Account);
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY);
    if (!stored) {
      setLoading(false);
      return;
    }
    setToken(stored);
    refresh(stored).finally(() => setLoading(false));
  }, [refresh]);

  const applySession = (accessToken: string, account: Account) => {
    localStorage.setItem(TOKEN_KEY, accessToken);
    setToken(accessToken);
    setUser(account);
  };

  const applyToken = useCallback(async (value: string) => {
    localStorage.setItem(TOKEN_KEY, value);
    setToken(value);
    await refresh(value);
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await fetch(`${API_URL}/api/v1/users/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!response.ok) throw new Error(await parseError(response));
    const payload = (await response.json()) as { access_token: string; user: Account };
    applySession(payload.access_token, payload.user);
  }, []);

  const register = useCallback(async (fullName: string, email: string, password: string) => {
    const response = await fetch(`${API_URL}/api/v1/users/register`, {
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
    const response = await fetch(`${API_URL}/api/v1/users/subscribe`, {
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
    const response = await fetch(`${API_URL}/api/checkout`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error(await parseError(response));
    const payload = (await response.json()) as { url: string };
    window.location.href = payload.url;
  }, [token]);

  const startOAuth = useCallback((provider: "google" | "apple") => {
    const next = window.location.pathname + window.location.search;
    window.location.href = `${API_URL}/api/v1/auth/${provider}/start?next=${encodeURIComponent(next || "/")}`;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
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
      startOAuth,
      applyToken,
      logout,
    }),
    [user, token, loading, authModalOpen, openAuthModal, closeAuthModal, login, register, subscribe, startCheckout, startOAuth, applyToken, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider");
  return context;
}
