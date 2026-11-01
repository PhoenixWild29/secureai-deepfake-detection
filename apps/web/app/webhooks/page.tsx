import { auth } from "@clerk/nextjs/server";
import { AuthGate } from "../auth-gate";
import { apiUrl, clerkEnabled } from "../../lib/clerk-config";
import { ClerkWebhooks } from "./clerk-webhooks";
import { WebhookPanel } from "./webhook-panel";

export default async function WebhooksPage() {
  const base = apiUrl();
  if (clerkEnabled()) {
    await auth.protect();
    return (
      <main>
        <p className="kicker">Workspace</p>
        <h1>Webhooks</h1>
        <p className="lede">
          Receive a JSON POST when a job in the selected workspace completes or fails.
        </p>
        <ClerkWebhooks apiUrl={base} />
      </main>
    );
  }
  if (process.env.NEXT_PUBLIC_AUTH_MODE === "dev") {
    return (
      <main>
        <p className="kicker">Local only</p>
        <h1>Webhooks</h1>
        <p className="lede">
          This workstation uses the dev credential. The URL is stored for the selected workspace.
        </p>
        <WebhookPanel apiUrl={base} token="dev" />
      </main>
    );
  }
  return <AuthGate title="Webhooks" />;
}
