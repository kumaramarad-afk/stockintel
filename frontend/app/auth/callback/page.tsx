"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";

import { useAuth } from "@/components/layout/AuthProvider";

function CallbackInner() {
  const params = useSearchParams();
  const router = useRouter();
  const { applyToken } = useAuth();

  useEffect(() => {
    const token = params.get("token");
    const next = params.get("next") || "/";
    if (!token) {
      router.replace("/login");
      return;
    }
    void applyToken(token).then(() => router.replace(next.startsWith("/") ? next : "/"));
  }, [applyToken, params, router]);

  return <p className="py-16 text-center text-gsr-muted">Signing you in…</p>;
}

export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<p className="py-16 text-center text-gsr-muted">Signing you in…</p>}>
      <CallbackInner />
    </Suspense>
  );
}
