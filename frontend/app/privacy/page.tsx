export default function PrivacyPage() {
  return (
    <article className="mx-auto max-w-3xl space-y-4 py-8 text-gsr-muted">
      <h1 className="text-3xl font-semibold text-white">Privacy Policy</h1>
      <p>Last updated September 6, 2026.</p>
      <p>
        GetStockReport collects the account details you provide when you register (name and email) and the research
        tickers you look up in your browser session. We use this information to operate the service, keep you signed in,
        and send newsletter issues if you subscribe.
      </p>
      <p>
        We share the minimum data needed with Google or Apple when you use social sign-in, and with Stripe when you
        subscribe. Market data is retrieved from public and licensed sources and is shown for informational purposes
        only.
      </p>
      <p>Contact research@getstockreport.com with privacy questions.</p>
    </article>
  );
}
