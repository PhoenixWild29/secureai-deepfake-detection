import Link from "next/link";

export default function HomePage() {
  return (
    <main>
      <p className="kicker">Guardian</p>
      <h1>SecureAI Guardian (rebuild)</h1>
      <p className="lede">
        Upload a short video. The API stores the bytes, a worker scores them on
        CPU, and this page shows the result. Job routes require a verified
        caller.
      </p>
      <div className="card">
        <p>
          Sign in with Clerk when the publishable key is configured. On a
          private workstation you can set the API to dev mode and this app to
          the same mode. Dev mode is not for a public host.
        </p>
        <p>
          <Link href="/upload">Upload a video</Link>
          {" · "}
          <Link href="/jobs">Job history</Link>
          {" · "}
          <Link href="/billing">Billing</Link>
        </p>
      </div>
    </main>
  );
}
