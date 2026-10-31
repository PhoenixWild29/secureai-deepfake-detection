import { auth } from "@clerk/nextjs/server";
import { AuthGate } from "../../auth-gate";
import { apiUrl, clerkEnabled } from "../../../lib/clerk-config";
import { ClerkJobReport } from "../clerk-jobs";
import { JobReport } from "../job-report";

export default async function JobReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const base = apiUrl();
  if (clerkEnabled()) {
    await auth.protect();
    return (
      <main>
        <p className="kicker">Report</p>
        <h1>Detection report</h1>
        <ClerkJobReport apiUrl={base} jobId={id} />
      </main>
    );
  }
  if (process.env.NEXT_PUBLIC_AUTH_MODE === "dev") {
    return (
      <main>
        <p className="kicker">Report</p>
        <h1>Detection report</h1>
        <JobReport apiUrl={base} jobId={id} token="dev" />
      </main>
    );
  }
  return <AuthGate title="Detection report" />;
}
