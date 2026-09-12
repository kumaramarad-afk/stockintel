import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-auto border-t border-slate-800/80 bg-slate-950">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-8 text-sm text-slate-400 sm:flex-row sm:items-center sm:justify-between">
        <p>GetStockReport © 2026</p>
        <p className="max-w-xl sm:text-center">
          For educational and informational purposes only. Not financial advice.
        </p>
        <div className="flex gap-4">
          <Link href="/privacy" className="hover:text-slate-100">
            Privacy Policy
          </Link>
          <Link href="/terms" className="hover:text-slate-100">
            Terms of Use
          </Link>
          <Link href="/legal/newsletter-disclaimer" className="hover:text-slate-100">
            Newsletter disclaimer
          </Link>
        </div>
      </div>
    </footer>
  );
}
