import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <p className="kicker">Rebuild</p>
      <h1>SecureAI Guardian (rebuild)</h1>
      <p className="lede">
        Saleable detection platform shell. This Next.js app replaces the legacy
        Guardian UI in a later phase. The Flask API and the old React tree stay
        in the repo as reference until the new services take over.
      </p>
      <div className="card">
        <p>
          Phase 0 queues a metadata stub only. Video bytes, Clerk sign-in, and
          real scores are not wired yet.
        </p>
        <p>
          <Link href="/upload">Open the upload placeholder</Link>
        </p>
      </div>
    </main>
  );
}
