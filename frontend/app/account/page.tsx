"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/components/layout/AuthProvider";
import { formatDate } from "@/lib/format";

export default function AccountPage() {
  const { user, loading, logout, startCheckout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (!user) {
    return <p className="py-16 text-center text-gsr-muted">Loading account…</p>;
  }

  return (
    <div className="mx-auto max-w-2xl py-8">
      <h1 className="text-3xl font-semibold">Account</h1>
      <p className="mt-2 text-gsr-muted">Your GetStockReport profile and plan.</p>
      <div className="glass-card mt-8 space-y-5 rounded-2xl p-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-gsr-muted">Name</p>
            <p className="mt-1 text-lg font-semibold">{user.full_name}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-gsr-muted">Email</p>
            <p className="mt-1 text-lg font-semibold">{user.email}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-gsr-muted">Plan</p>
            <p className="mt-1 text-lg font-semibold capitalize text-gsr-accent">{user.plan}</p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-gsr-muted">Reports this month</p>
            <p className="mt-1 text-lg font-semibold">
              {user.plan === "pro" ? "Unlimited" : `${user.reports_used ?? 0} / ${user.reports_limit ?? 5}`}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-gsr-muted">Member since</p>
            <p className="mt-1 text-lg font-semibold">{formatDate(user.created_at)}</p>
          </div>
        </div>
        {user.subscribed_at && (
          <p className="text-sm text-gsr-muted">Pro since {formatDate(user.subscribed_at)}</p>
        )}
        <div className="flex flex-wrap gap-3 pt-2">
          {user.plan === "pro" ? (
            <Link
              href="/subscribe"
              className="rounded-xl bg-gsr-accent px-5 py-2.5 text-sm font-semibold text-gsr-bg hover:brightness-110"
            >
              Manage plan
            </Link>
          ) : (
            <button
              type="button"
              onClick={() => void startCheckout().catch(() => router.push("/subscribe"))}
              className="rounded-xl bg-gsr-accent px-5 py-2.5 text-sm font-semibold text-gsr-bg hover:brightness-110"
            >
              🔒 Unlock Full Analyst Briefing ($7/mo)
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              logout();
              router.push("/");
            }}
            className="rounded-xl border border-gsr-border px-5 py-2.5 text-sm hover:border-white/40"
          >
            Sign out
          </button>
        </div>
      </div>
    </div>
  );
}
