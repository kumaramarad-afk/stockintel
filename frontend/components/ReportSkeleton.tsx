"use client";

/** Lightweight shimmer placeholders while a report loads. */
export function ReportSkeleton() {
  return (
    <div className="animate-pulse space-y-4" aria-hidden>
      <div className="rounded-2xl border border-slate-200 bg-white px-5 py-6">
        <div className="h-3 w-28 rounded bg-slate-200" />
        <div className="mt-3 h-8 w-48 rounded bg-slate-200" />
        <div className="mt-2 h-4 w-24 rounded bg-slate-100" />
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white px-5 py-8 sm:px-8">
        <div className="h-5 w-40 rounded bg-slate-200" />
        <div className="mt-4 space-y-3">
          <div className="h-3 w-full rounded bg-slate-100" />
          <div className="h-3 w-[92%] rounded bg-slate-100" />
          <div className="h-3 w-[85%] rounded bg-slate-100" />
          <div className="h-3 w-[70%] rounded bg-slate-100" />
        </div>
        <div className="mt-8 h-5 w-52 rounded bg-slate-200" />
        <div className="mt-4 space-y-3">
          <div className="h-3 w-full rounded bg-slate-100" />
          <div className="h-3 w-[88%] rounded bg-slate-100" />
          <div className="h-3 w-[76%] rounded bg-slate-100" />
        </div>
      </div>
    </div>
  );
}
