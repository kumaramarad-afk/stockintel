"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/layout/AuthProvider";
import { MarketTicker } from "@/components/layout/MarketTicker";

const nav = [
  { href: "/research", label: "Research" },
  { href: "/newsletter", label: "Newsletter" },
];

export function Header() {
  const pathname = usePathname();
  const { user, loading } = useAuth();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(true);
  }, []);

  return (
    <header className="sticky top-0 z-40">
      <MarketTicker />
      <div className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5">
          <Link href="/" className="flex items-center gap-2.5">
            <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500 text-sm font-bold text-slate-950">
              GS
            </span>
            <span className="text-lg font-semibold tracking-tight text-slate-100">GetStockReport</span>
          </Link>
          <nav className="flex items-center gap-5 text-sm text-slate-400">
            {nav.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`transition hover:text-slate-100 ${ready && (pathname === item.href || (item.href === "/research" && pathname === "/")) ? "text-slate-100" : ""}`}
              >
                {item.label}
              </Link>
            ))}
            <Link href="/subscribe" className="hidden text-emerald-400 hover:text-emerald-300 sm:inline">
              Subscribe
            </Link>
            {ready && user ? (
              <Link
                href="/account"
                className="rounded-full border border-slate-700/60 bg-slate-800 px-5 py-2 text-sm text-slate-200 transition-all hover:bg-slate-700"
              >
                {user.full_name.split(" ")[0]}
              </Link>
            ) : ready && !loading ? (
              <Link
                href="/login"
                className="rounded-full border border-slate-700/60 bg-slate-800 px-5 py-2 text-sm text-slate-200 transition-all hover:bg-slate-700"
              >
                Sign in
              </Link>
            ) : (
              <span className="rounded-full border border-slate-800 px-5 py-2 text-sm text-slate-500">…</span>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
}
