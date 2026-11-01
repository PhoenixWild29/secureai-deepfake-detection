import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Privacy · SecureAI",
  description: "What Guardian stores when you upload a video and open a job.",
};

export default function PrivacyPage() {
  return (
    <main className="prose">
      <p className="kicker">Privacy</p>
      <h1>Privacy</h1>
      <p className="lede">
        This page describes the rebuild product under <code>apps/</code>. It is a product notice, not a
        lawyer-drafted policy for a specific company entity.
      </p>
      <h2>What a job stores</h2>
      <ul>
        <li>The video bytes, under an object key scoped to your account.</li>
        <li>The filename, content type, size, and an etag captured when the job is created.</li>
        <li>A job row: status, prediction, confidence, and, when the CPU detector finishes, a short JSON note of the signals.</li>
        <li>Your Clerk user id. A workspace job also stores the organization id and is visible to members of that workspace.</li>
      </ul>
      <h2>What this release does not do</h2>
      <ul>
        <li>It does not train a model on your upload.</li>
        <li>It does not sell the file or the score.</li>
        <li>It does not put the video on a public URL. Job routes require the account that owns the job, or a member of its workspace.</li>
      </ul>
      <h2>Billing</h2>
      <p>
        Checkout and the customer portal run through Stripe when that integration is configured. Stripe
        receives the customer and subscription identifiers needed to charge the plan. Card numbers stay
        with Stripe.
      </p>
      <h2>Contact</h2>
      <p>
        Report a security or privacy issue through the contact on{" "}
        <a href="/.well-known/security.txt">/.well-known/security.txt</a>. Read{" "}
        <Link href="/docs">how detection works</Link> before you rely on a score.
      </p>
    </main>
  );
}
