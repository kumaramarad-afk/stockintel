"use client";

import { useEffect, useState } from "react";

/** Top-of-page loading bar (YouTube/Stripe style). */
export function LoadingProgressBar({ isLoading }: { isLoading: boolean }) {
  const [progress, setProgress] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let interval: number | undefined;
    let hideTimer: number | undefined;

    if (isLoading) {
      setVisible(true);
      setProgress(8);
      interval = window.setInterval(() => {
        setProgress((prev) => {
          if (prev >= 90) return prev;
          return Math.min(90, prev + 8 + Math.random() * 12);
        });
      }, 220);
    } else if (visible) {
      setProgress(100);
      hideTimer = window.setTimeout(() => {
        setVisible(false);
        setProgress(0);
      }, 320);
    }

    return () => {
      if (interval) window.clearInterval(interval);
      if (hideTimer) window.clearTimeout(hideTimer);
    };
  }, [isLoading, visible]);

  if (!visible && progress === 0) return null;

  return (
    <div
      aria-hidden
      className="pointer-events-none fixed left-0 top-0 z-[9999] h-[3px] bg-emerald-400 transition-[width] duration-200 ease-out"
      style={{ width: `${progress}%`, transition: progress === 0 ? "none" : undefined }}
    />
  );
}
