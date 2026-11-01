import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Terms · SecureAI",
  description: "Terms for using Guardian detection jobs.",
};

export default function TermsPage() {
  return (
    <main className="prose">
      <p className="kicker">Terms</p>
      <h1>Terms</h1>
      <p className="lede">
        These terms cover the Guardian rebuild. They are a plain-language product agreement, not a
        substitute for counsel.
      </p>
      <h2>Your uploads</h2>
      <p>
        Upload only video you have the right to analyze. You are responsible for the file, the filename,
        and what you do with the score.
      </p>
      <h2>The score</h2>
      <p>
        A completed job is a CPU heuristic. It can be wrong in both directions. It is not legal evidence,
        not a guarantee that a clip is real or synthetic, and not a promise of a particular accuracy. See{" "}
        <Link href="/docs">how detection works</Link> for the signals and the limits.
      </p>
      <h2>Plans</h2>
      <p>
        Free trial, Pro, and Team caps count each created job, including jobs that fail. A batch counts
        as one job per item. Exceeding the cap stops new jobs until the next period or an upgrade.
        Uploads stay on a shorter rate limit.
      </p>
      <h2>The service</h2>
      <p>
        Routes, quotas, and the detector can change. A workspace owner can register one HTTPS URL for
        job results. PDF reports are not part of this release. API keys for unattended Pro access are
        not issued yet.
      </p>
    </main>
  );
}
