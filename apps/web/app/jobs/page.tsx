import { auth } from "@clerk/nextjs/server";
import { AuthGate } from "../auth-gate";
import { apiUrl, clerkEnabled } from "../../lib/clerk-config";
import { ClerkJobList } from "./clerk-jobs";
import { JobList } from "./job-list";

export default async function JobsPage() {
  const base = apiUrl();
  if (clerkEnabled()) {
    await auth.protect();
    return (
      <main>
        <p className="kicker">Account</p>
        <h1>History</h1>
        <p className="lede">
          Jobs for the signed-in account. Newest first. A job that is still queued or processing updates
          here until it finishes.
        </p>
        <ClerkJobList apiUrl={base} />
      </main>
    );
  }
  if (process.env.NEXT_PUBLIC_AUTH_MODE === "dev") {
    return (
      <main>
        <p className="kicker">Local only</p>
        <h1>History</h1>
        <p className="lede">
          Jobs for the dev credential on this workstation. Newest first. A job that is still queued or
          processing updates here until it finishes.
        </p>
        <JobList apiUrl={base} token="dev" />
      </main>
    );
  }
  return <AuthGate title="History" />;
}
