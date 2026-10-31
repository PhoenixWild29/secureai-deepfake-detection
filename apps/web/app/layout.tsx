import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "SecureAI Guardian",
  description:
    "Phase 0 rebuild of SecureAI Guardian. Detection, auth, and uploads land in later phases.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body>
        <div className="shell">
          <nav className="nav">
            <strong>SecureAI</strong>
            <Link href="/">Home</Link>
            <Link href="/upload">Upload</Link>
          </nav>
          {children}
        </div>
      </body>
    </html>
  );
}
