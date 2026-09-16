import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { AnalyticsScripts } from "@/components/layout/AnalyticsScripts";
import { AuthModal } from "@/components/auth/AuthModal";
import { AuthProvider } from "@/components/layout/AuthProvider";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  metadataBase: new URL("https://getstockreport.com"),
  title: {
    default: "GetStockReport — Research that shows the reasoning, not a verdict",
    template: "%s | GetStockReport",
  },
  description: "Bull case, bear case, what has to be true — you decide. Institutional-style stock research without buy/sell calls.",
  openGraph: {
    siteName: "GetStockReport",
    type: "website",
    images: [{ url: "/og-image.svg" }],
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <AnalyticsScripts />
      </head>
      <body className={`${inter.variable} ${inter.className}`}>
        <AuthProvider>
          <div className="flex min-h-screen flex-col bg-slate-950">
            <Header />
            <main className="mx-auto w-full max-w-6xl flex-1 px-6 py-8">{children}</main>
            <Footer />
          </div>
          <AuthModal />
        </AuthProvider>
      </body>
    </html>
  );
}
