import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import Link from "next/link"
import "./globals.css"

const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
})

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
})

export const metadata: Metadata = {
  title: "PL Predictor — Premier League Statistical Forecasting",
  description:
    "32 seasons of data. Dixon-Coles model. 1,000 Monte Carlo simulations. " +
    "Predicting the Premier League 2026–2037.",
}

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-[#080c14] text-white">
        <header className="sticky top-0 z-50 border-b border-white/8 bg-[#080c14]/80 backdrop-blur">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 flex h-14 items-center justify-between">
            <Link
              href="/"
              className="text-[#00d4ff] font-bold text-lg tracking-tight hover:opacity-80 transition"
            >
              PL Predictor
            </Link>
            <nav className="flex gap-6 text-sm text-white/70">
              <Link href="/historical" className="hover:text-white transition">
                Historical
              </Link>
              <Link href="/predictions" className="hover:text-white transition">
                Predictions
              </Link>
            </nav>
          </div>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="border-t border-white/8 py-6 text-center text-xs text-white/30">
          Data: football-data.co.uk · FPL API · Dixon-Coles (1997)
        </footer>
      </body>
    </html>
  )
}
