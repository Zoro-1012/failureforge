import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "FailureForge",
  description: "Distributed systems failure simulation & AI diagnosis benchmark",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-forge-border bg-forge-panel">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="flex items-center gap-2">
              <span className="text-lg font-semibold text-white">
                Failure<span className="text-forge-accent">Forge</span>
              </span>
              <span className="rounded bg-forge-border px-2 py-0.5 text-xs text-slate-400">
                AI diagnosis benchmark
              </span>
            </Link>
            <nav className="text-sm text-slate-400">
              <Link href="/" className="hover:text-white">
                Dashboard
              </Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
