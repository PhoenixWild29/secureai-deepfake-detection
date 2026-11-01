import { auth } from "@clerk/nextjs/server";
import { AuthGate } from "../auth-gate";
import { apiUrl, clerkEnabled } from "../../lib/clerk-config";
import { BillingPanel } from "./billing-panel";
import { ClerkBilling } from "./clerk-billing";

export default async function BillingPage({
  searchParams,
}: {
  searchParams: Promise<{ checkout?: string }>;
}) {
  const base = apiUrl();
  const query = await searchParams;
  const notice =
    query.checkout === "success"
      ? "Payment received. The plan updates when Stripe notifies the API."
      : query.checkout === "cancel"
        ? "Checkout was canceled. The current plan is unchanged."
        : null;
  if (clerkEnabled()) {
    await auth.protect();
    return (
      <main>
        <p className="kicker">Account</p>
        <h1>Billing</h1>
        <p className="lede">Plan, remaining jobs, and workspaces for the signed-in account.</p>
        <ClerkBilling apiUrl={base} notice={notice} />
      </main>
    );
  }
  if (process.env.NEXT_PUBLIC_AUTH_MODE === "dev") {
    return (
      <main>
        <p className="kicker">Local only</p>
        <h1>Billing</h1>
        <p className="lede">
          This workstation uses the dev credential. Stripe stays in test mode, and an empty
          Stripe key disables Checkout.
        </p>
        <BillingPanel apiUrl={base} token="dev" notice={notice} />
      </main>
    );
  }
  return <AuthGate title="Billing" />;
}
