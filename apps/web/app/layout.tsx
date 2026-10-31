import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import { AuthButtons } from "./auth-buttons";
import "./globals.css";

export const metadata: Metadata = {
  title: "SecureAI Guardian",
  description: "Upload a short video and read a CPU detection result.",
};

function clerkEnabled(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY);
}

function Shell({ children, showAuth }: { children: ReactNode; showAuth: boolean }) {
  return (
    <>
      <nav className="nav">
        <strong>SecureAI</strong>
        <Link href="/">Home</Link>
        <Link href="/upload">Upload</Link>
        {showAuth ? <AuthButtons /> : null}
      </nav>
      {children}
    </>
  );
}

export default function RootLayout({ children }: { children: ReactNode }) {
  const enabled = clerkEnabled();
  const shell = <Shell showAuth={enabled}>{children}</Shell>;
  return (
    <html lang="en">
      <body>
        <div className="shell">{enabled ? <ClerkProvider>{shell}</ClerkProvider> : shell}</div>
      </body>
    </html>
  );
}
