import { ClerkProvider } from "@clerk/nextjs";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import Link from "next/link";
import { AuthButtons } from "./auth-buttons";
import { apiUrl, clerkEnabled } from "../lib/clerk-config";
import { WorkspaceProvider, WorkspaceSwitcher } from "./workspace";
import "./globals.css";

export const metadata: Metadata = {
  title: "SecureAI Guardian",
  description: "Upload a short video and read a CPU detection result.",
};

function Shell({
  children,
  mode,
  api,
}: {
  children: ReactNode;
  mode: "clerk" | "dev" | "off";
  api: string;
}) {
  return (
    <WorkspaceProvider>
      <nav className="nav">
        <strong>SecureAI</strong>
        <Link href="/">Home</Link>
        <Link href="/upload">Upload</Link>
        <Link href="/jobs">History</Link>
        <Link href="/billing">Billing</Link>
        <Link href="/webhooks">Webhooks</Link>
        <Link href="/keys">API keys</Link>
        <Link href="/docs">Docs</Link>
        {mode === "off" ? null : <WorkspaceSwitcher mode={mode} apiUrl={api} />}
        {mode === "clerk" ? <AuthButtons /> : null}
      </nav>
      {children}
      <footer className="footer">
        <Link href="/docs">How detection works</Link>
        <Link href="/privacy">Privacy</Link>
        <Link href="/terms">Terms</Link>
      </footer>
    </WorkspaceProvider>
  );
}

export default function RootLayout({ children }: { children: ReactNode }) {
  const enabled = clerkEnabled();
  const dev = process.env.NEXT_PUBLIC_AUTH_MODE === "dev";
  const mode = enabled ? "clerk" : dev ? "dev" : "off";
  const shell = (
    <Shell mode={mode} api={apiUrl()}>
      {children}
    </Shell>
  );
  return (
    <html lang="en">
      <body>
        <div className="shell">{enabled ? <ClerkProvider>{shell}</ClerkProvider> : shell}</div>
      </body>
    </html>
  );
}
