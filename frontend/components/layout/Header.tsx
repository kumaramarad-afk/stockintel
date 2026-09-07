"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/components/layout/AuthProvider";

const nav = [
  { href: "/", label: "Research" },
  { href: "/newsletter", label: "Newsletter" },
];

export function Header() {
  const pathname = usePathname();
  const { user } = useAuth();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setReady(true);
  }, []);

  return (
    <header className="sticky top-0 z-40 border-b border-gsr-border/80 bg-gsr-bg/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2.5">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gsr-accent text-sm font-bold text-gsr-bg">
            GS
          </span>
          <span className="text-lg font-semibold tracking-tight">GetStockReport</span>
        </Link>
        <nav className="flex items-center gap-5 text-sm text-gsr-muted">
          {nav.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`transition hover:text-white ${ready && pathname === item.href ? "text-white" : ""}`}
            >
              {item.label}
            </Link>
          ))}
          <Link href="/subscribe" className="hidden text-gsr-accent hover:text-white sm:inline">
            Subscribe
          </Link>
          {ready && user ? (
            <Link
              href="/account"
              className="rounded-full border border-gsr-border bg-gsr-card px-3 py-1.5 text-white hover:border-gsr-accent/40"
            >
              {user.full_name.split(" ")[0]}
            </Link>
          ) : (
            <Link
              href="/login"
              className="rounded-full bg-gsr-accent px-3.5 py-1.5 font-semibold text-gsr-bg hover:brightness-110"
            >
              Sign in
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
