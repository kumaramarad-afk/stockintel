"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect } from "react";

import { useAuth } from "@/components/layout/AuthProvider";
import { postLoginPath, RESEARCH_PATH } from "@/lib/auth";

function CallbackInner() {
  const params = useSearchParams();
  const router = useRouter();
  const { applyToken } = useAuth();

  useEffect(() => {
    const token = params.get("token");
    const next = postLoginPath(params.get("next") || RESEARCH_PATH);
    if (!token) {
      router.replace("/login");
      return;
    }
    void applyToken(token)
      .then(() => {
        window.location.replace(next);
      })
      .catch(() => router.replace("/login"));
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
