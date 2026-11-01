import { auth } from "@clerk/nextjs/server";
import { AuthGate } from "../auth-gate";
import { apiUrl, clerkEnabled } from "../../lib/clerk-config";
import { ClerkKeys } from "./clerk-keys";
import { KeyPanel } from "./key-panel";

export default async function KeysPage() {
  const base = apiUrl();
  if (clerkEnabled()) {
    await auth.protect();
    return (
      <main>
        <p className="kicker">Account</p>
        <h1>API keys</h1>
        <p className="lede">
          Call the detection API with a secret instead of a browser session. The header workspace
          chooses a personal key or a workspace key.
        </p>
        <ClerkKeys apiUrl={base} />
      </main>
    );
  }
  if (process.env.NEXT_PUBLIC_AUTH_MODE === "dev") {
    return (
      <main>
        <p className="kicker">Local only</p>
        <h1>API keys</h1>
        <p className="lede">
          This workstation uses the dev credential to mint keys. Callers then send the <code>sai_</code> secret.
        </p>
        <KeyPanel apiUrl={base} token="dev" />
      </main>
    );
  }
  return <AuthGate title="API keys" />;
}
