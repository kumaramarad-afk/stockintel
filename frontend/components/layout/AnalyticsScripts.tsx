import Script from "next/script";

const PLAUSIBLE_SCRIPT_SRC =
  process.env.NEXT_PUBLIC_PLAUSIBLE_SCRIPT_SRC ||
  (process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN
    ? "https://plausible.io/js/pa-NotWC3yuaBdW_51Jp2LLX.js"
    : undefined);
const GA_ID = process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID;

export function AnalyticsScripts() {
  return (
    <>
      {PLAUSIBLE_SCRIPT_SRC ? (
        <>
          {/* Privacy-friendly analytics by Plausible */}
          <Script async src={PLAUSIBLE_SCRIPT_SRC} strategy="beforeInteractive" />
          <Script id="plausible-init" strategy="beforeInteractive">
            {`window.plausible=window.plausible||function(){(plausible.q=plausible.q||[]).push(arguments)},plausible.init=plausible.init||function(i){plausible.o=i||{}};plausible.init()`}
          </Script>
        </>
      ) : null}
      {GA_ID ? (
        <>
          <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`} strategy="afterInteractive" />
          <Script id="ga-init" strategy="afterInteractive">
            {`window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js', new Date());gtag('config','${GA_ID}');`}
          </Script>
        </>
      ) : null}
    </>
  );
}
