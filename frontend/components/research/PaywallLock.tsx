import type { ReactNode } from "react";

import { useAuth } from "@/components/layout/AuthProvider";

export function UpgradeButton({ className = "" }: { className?: string }) {
  const { user, startCheckout, openAuthModal } = useAuth();

  async function onClick() {
    if (!user) {
      openAuthModal();
      return;
    }
    try {
      await startCheckout();
    } catch (error) {
      window.location.href = "/subscribe";
    }
  }

  return (
    <button
      type="button"
      onClick={() => void onClick()}
      className={`rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-slate-950 shadow-lg shadow-emerald-500/20 transition-all hover:bg-emerald-400 ${className}`}
    >
      🔒 Unlock Full Analyst Briefing ($7/mo)
    </button>
  );
}

export function PaywallLock({
  locked,
  children,
  minHeight = "min-h-[7rem]",
}: {
  locked: boolean;
  children: ReactNode;
  minHeight?: string;
}) {
  if (!locked) return <>{children}</>;
  return (
    <div className={`relative ${minHeight}`}>
      <div className="paywall-blur pointer-events-none select-none">{children}</div>
      <div className="absolute inset-0 flex items-center justify-center bg-gsr-bg/40 px-4">
        <UpgradeButton />
      </div>
    </div>
  );
}
