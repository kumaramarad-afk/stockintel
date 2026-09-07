import type { Metadata } from "next";
import { Inter } from "next/font/google";

import { AuthModal } from "@/components/auth/AuthModal";
import { AuthProvider } from "@/components/layout/AuthProvider";
import { Footer } from "@/components/layout/Footer";
import { Header } from "@/components/layout/Header";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata: Metadata = {
  title: "GetStockReport — Institutional-grade stock research. Free.",
  description: "Institutional-grade stock research. Free.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${inter.variable} ${inter.className}`}>
        <AuthProvider>
          <div className="flex min-h-screen flex-col bg-gsr-bg">
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
