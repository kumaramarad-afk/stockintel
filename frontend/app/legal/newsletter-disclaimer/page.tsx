import Link from "next/link";

export default function NewsletterDisclaimerPage() {
  return (
    <article className="mx-auto max-w-3xl space-y-4 py-8 text-gsr-muted">
      <h1 className="text-3xl font-semibold text-white">Newsletter Disclaimer</h1>
      <p>Last updated September 12, 2026.</p>
      <p>
        The GetStockReport daily briefing is for educational and informational purposes only. It is not financial,
        investment, legal, or tax advice. GetStockReport is not a SEBI, SEC, or FINRA-registered investment adviser or
        broker-dealer.
      </p>
      <p>
        Nothing in the briefing is a recommendation to buy, sell, or hold any security. Coverage uses neutral score
        bands: Bullish Consensus, Mixed Signals, and Bearish Consensus. Insider Form 4 activity and 13F holdings are
        historical public filings and are not signals to transact.
      </p>
      <p>
        Market data can be incomplete, delayed, or wrong. Past performance is not future results. You assume full
        responsibility for any investment decision. Verify independently and consult a licensed advisor before acting.
      </p>
      <p>
        Premium is billed at $12 per month until canceled and includes unlimited research, the weekday 8 AM UTC
        briefing, and a 90-day archive.
      </p>
      <p>
        <Link href="/privacy" className="text-gsr-accent hover:underline">
          Privacy Policy
        </Link>
        {" · "}
        <Link href="/terms" className="text-gsr-accent hover:underline">
          Terms of Use
        </Link>
        {" · "}
        <Link href="/newsletter" className="text-gsr-accent hover:underline">
          Newsletter desk
        </Link>
      </p>
    </article>
  );
}
