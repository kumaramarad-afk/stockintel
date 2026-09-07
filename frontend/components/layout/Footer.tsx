import Link from "next/link";

export function Footer() {
  return (
    <footer className="mt-auto border-t border-gsr-border bg-gsr-bg">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-6 py-8 text-sm text-gsr-muted sm:flex-row sm:items-center sm:justify-between">
        <p>GetStockReport © 2026</p>
        <p className="max-w-xl sm:text-center">
          For educational and informational purposes only. Not financial advice.
        </p>
        <div className="flex gap-4">
          <Link href="/privacy" className="hover:text-white">
            Privacy Policy
          </Link>
          <Link href="/terms" className="hover:text-white">
            Terms of Use
          </Link>
        </div>
      </div>
    </footer>
  );
}
