"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";

import { PlanExceptionAdmin } from "@/components/account/PlanExceptionAdmin";
import { useAuth } from "@/components/layout/AuthProvider";
import { formatDate } from "@/lib/format";
import { isPaidPlan, planLabel } from "@/lib/plans";
import { readToken } from "@/lib/session";

function AccountInner() {
  const { user, loading, logout, startCheckout, startBillingPortal, refreshProfile, verifyCheckoutSession, token } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const [portalError, setPortalError] = useState<string | null>(null);
  const [portalBusy, setPortalBusy] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const synced = useRef(false);

  useEffect(() => {
    if (loading) return;
    if (!user && !readToken()) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  useEffect(() => {
    if (loading || synced.current) return;
    if (params.get("upgraded") !== "1") return;
    synced.current = true;
    const sessionId = params.get("session_id");
    setSyncing(true);
    void (async () => {
      try {
        await verifyCheckoutSession(sessionId);
      } catch {
        await refreshProfile();
      } finally {
        setSyncing(false);
        router.replace("/account");
      }
    })();
  }, [loading, params, refreshProfile, router, verifyCheckoutSession]);

  if (!user) {
    return <p className="py-16 text-center text-gsr-muted">Loading account…</p>;
  }

  return (
    <div className="mx-auto max-w-2xl py-8">
      <h1 className="text-3xl font-semibold">Account</h1>
      <p className="mt-2 text-gsr-muted">Your GetStockReport profile and plan.</p>
      {syncing && <p className="mt-3 text-sm text-gsr-accent">Confirming your Premium subscription…</p>}
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
            <p className="mt-1 text-lg font-semibold capitalize text-gsr-accent">
              {planLabel(user.plan)}
              {user.complimentary ? " (complimentary)" : ""}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-gsr-muted">Free reports remaining this month</p>
            <p className="mt-1 text-lg font-semibold">
              {isPaidPlan(user.plan)
                ? "Unlimited"
                : `${user.reports_remaining ?? Math.max(0, (user.reports_limit ?? 5) - (user.reports_used ?? 0))} / ${user.reports_limit ?? 5}`}
            </p>
          </div>
          <div>
            <p className="text-xs uppercase tracking-[0.16em] text-gsr-muted">Member since</p>
            <p className="mt-1 text-lg font-semibold">{formatDate(user.created_at)}</p>
          </div>
        </div>
        {user.subscribed_at && (
          <p className="text-sm text-gsr-muted">Premium since {formatDate(user.subscribed_at)}</p>
        )}
        <div className="flex flex-wrap gap-3 pt-2">
          {isPaidPlan(user.plan) ? (
            user.complimentary ? (
              <p className="rounded-xl border border-gsr-border px-5 py-2.5 text-sm text-gsr-muted">
                Complimentary Premium ($12 equivalent). No Stripe billing on this account.
              </p>
            ) : (
              <button
                type="button"
                disabled={portalBusy}
                onClick={() => {
                  setPortalBusy(true);
                  setPortalError(null);
                  void startBillingPortal()
                    .catch((err) => setPortalError(err instanceof Error ? err.message : "Could not open billing portal"))
                    .finally(() => setPortalBusy(false));
                }}
                className="rounded-xl bg-gsr-accent px-5 py-2.5 text-sm font-semibold text-gsr-bg hover:brightness-110 disabled:opacity-60"
              >
                {portalBusy ? "Opening…" : "Manage Subscription"}
              </button>
            )
          ) : (
            <button
              type="button"
              onClick={() => void startCheckout().catch(() => router.push("/subscribe"))}
              className="rounded-xl bg-gsr-accent px-5 py-2.5 text-sm font-semibold text-gsr-bg hover:brightness-110"
            >
              Unlock Premium ($12/mo)
            </button>
          )}
          <button
            type="button"
            onClick={() => router.push("/newsletter")}
            className="rounded-xl border border-gsr-border px-5 py-2.5 text-sm hover:border-white/40"
          >
            Newsletter desk
          </button>
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
        {portalError && <p className="text-sm text-rose-400">{portalError}</p>}
      </div>
      {user.is_admin && token && <PlanExceptionAdmin token={token} />}
    </div>
  );
}

export default function AccountPage() {
  return (
    <Suspense fallback={<p className="py-16 text-center text-gsr-muted">Loading account…</p>}>
      <AccountInner />
    </Suspense>
  );
}
