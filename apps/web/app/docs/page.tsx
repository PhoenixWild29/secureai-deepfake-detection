import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "How detection works · SecureAI",
  description: "What the CPU detector scores, what it does not prove, and how API access works today.",
};

export default function DocsPage() {
  return (
    <main className="prose">
      <p className="kicker">Docs</p>
      <h1>How detection works</h1>
      <p className="lede">
        Guardian scores a short video on CPU. The result is a heuristic, not a
        lab certificate and not a trained deepfake classifier.
      </p>
      <h2>What runs today</h2>
      <p>
        The default detector samples frames from the file you uploaded. It does
        not download GPU weights. Each completed job can include four signals.
        Higher means the clip looks more synthetic to this formula:
      </p>
      <ul>
        <li>Texture: high-frequency energy. A flat frame scores low. Heavy noise scores high.</li>
        <li>Motion: how much sampled frames differ.</li>
        <li>Temporal: flicker and histogram disagreement between frames. One readable frame adds nothing here.</li>
        <li>
          Region: a face box from OpenCV&apos;s bundled cascade when that file loads, otherwise a skin-tone
          region. The score rises when the seam is much sharper than the interior. No region scores 0, which
          means &quot;no cue&quot;, not &quot;real&quot;.
        </li>
      </ul>
      <p>
        Those signals are mixed with fixed weights. <code>DETECTOR_MODE=stub</code> skips the file and is
        only for tests.
      </p>
      <h2>Limits</h2>
      <ul>
        <li>There is no published accuracy on a labeled deepfake benchmark for this scorer.</li>
        <li>A noisy real video can score as fake. A careful synthetic video can score as real.</li>
        <li>Sharp cutouts and ordinary edges can raise the region cue. Absence of a face is not a verdict.</li>
        <li>Do not use the score as legal evidence or as the only reason to publish, accuse, or remove a clip.</li>
        <li>The legacy GPU ensemble, attestation, and Solana anchoring are not in this product yet.</li>
      </ul>
      <h2>API access</h2>
      <p>
        Job routes require a verified Clerk session. The browser sends that session token. Uploads and{" "}
        <code>POST /v1/jobs</code> are rate limited, and the monthly plan cap applies to each job, including
        jobs that later fail.
      </p>
      <p>
        <code>POST /v1/jobs/batch</code> accepts up to 10 stored object keys, charges the same jobs rate
        limit once per item, and checks the same quota before inserting rows.{" "}
        <code>GET /v1/jobs/{"{id}"}/report</code> downloads a completed job as JSON.
      </p>
      <p>
        Pro API keys are not issued yet. TODO: mint scoped keys for Pro and Team workspaces. Until then,
        sign in with Clerk (or the private dev bypass on a workstation) and call the job routes with the
        session token.
      </p>
      <p>
        PDF export is not available yet. TODO: render the same JSON report to PDF without adding a heavy
        dependency first.
      </p>
      <p>
        <Link href="/privacy">Privacy</Link>
        {" · "}
        <Link href="/terms">Terms</Link>
        {" · "}
        <a href="/.well-known/security.txt">security.txt</a>
      </p>
    </main>
  );
}
