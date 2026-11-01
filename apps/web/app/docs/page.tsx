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
        <li>The legacy GPU ensemble and Solana anchoring are not in this product.</li>
      </ul>
      <h2>API access</h2>
      <p>
        Job routes require a verified Clerk session. The browser sends that session token. Uploads and{" "}
        <code>POST /v1/jobs</code> are rate limited, and the monthly plan cap applies to each job, including
        jobs that later fail.
      </p>
      <p>
        <code>POST /v1/jobs/batch</code> accepts up to 10 stored object keys, charges the same jobs rate
        limit once per item, and checks the same quota before inserting rows. If the queue stops after
        some ids are accepted, the 202 response lists those jobs and the ids that did not queue. Those
        ids do not spend the monthly cap. If nothing was queued, the response is 503 and the detail is{" "}
        <code>Could not queue the job.</code>{" "}
        <code>GET /v1/jobs/{"{id}"}/report</code> downloads a completed job as JSON.{" "}
        <code>GET /v1/jobs/{"{id}"}/report.pdf</code> downloads the same fields as a one-page PDF.{" "}
        <code>POST /v1/jobs/{"{id}"}/attest</code> signs that completed report for a Pro or Team plan.
        PDF uses that same plan rule. A private workstation in dev mode with quotas left unlimited can
        download the PDF on the free plan. The file repeats the limitations above and is not legal evidence.
      </p>
      <h2 id="attestation">Signed attestation</h2>
      <p>
        A completed report can be signed with the API&apos;s Ed25519 key. The signature covers one compact JSON
        string: job id, organization id (null for a personal job), status, prediction, confidence, model, signals,
        updated time, and the same limitations text as the report. Guardian downloads that document from a completed
        report.
      </p>
      <p>
        The signature shows that this API issued those bytes. It does not show that the clip is real or synthetic,
        and it is not legal evidence. The detector limits above still apply. SecureAI does not put the signature
        on Solana or any other chain.
      </p>
      <p>
        Anyone can check it without an account. <code>POST /v1/attestations/verify</code> takes the exact{" "}
        <code>payload</code> string, the standard base64 <code>signature</code>, and an optional <code>key_id</code>.
        Do not parse the payload and encode it again. <code>GET /v1/attestations/keys</code> returns the public
        key. A valid verify response includes that public key too. If the server has no attestation key, these
        routes answer 503 and Guardian shows a short note instead of the download. Issuing requires Pro or
        Team. A private workstation in dev mode with quotas left unlimited can issue on the free plan.
        Checking a signature does not require a plan or an account. The server keeps one signing key.
        After that key or its id is rotated, signatures from the previous key id no longer verify.
      </p>
      <p>
        Pro and Team can mint a key from the <Link href="/keys">API keys</Link> page. The secret starts
        with <code>sai_</code>, is shown once, and is stored only as a SHA-256 hash. Send{" "}
        <code>Authorization: Bearer sai_…</code>. A personal key may send <code>X-Org-Id</code>, and that
        workspace has to be Pro or Team. A workspace key stays inside that workspace, including
        member, webhook, Checkout, and portal routes that name an organization in the path or body.
        It cannot create another workspace. Team Checkout with no organization id uses the bound
        workspace. If its creator is
        removed or demoted from owner or admin, the next use hard-revokes that key (401). Promoting them
        later does not restore it. Free plans cannot create or use a key, including on a private
        workstation. Revoking a key rejects it on the next request. Clerk session tokens still work, and{" "}
        <code>AUTH_MODE=dev</code> still accepts <code>Bearer dev</code>.
      </p>
      <p>
        A workspace owner can register one HTTPS URL. The worker POSTs the job id, status, prediction,
        confidence, organization id, and timestamp when that workspace&apos;s job finishes. An optional
        secret adds <code>X-SecureAI-Signature</code>. Personal jobs do not fire it.
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
