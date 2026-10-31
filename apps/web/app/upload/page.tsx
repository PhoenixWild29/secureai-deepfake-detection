import { auth } from "@clerk/nextjs/server";
import { AuthGate } from "../auth-gate";
import { apiUrl, clerkEnabled } from "../../lib/clerk-config";
import { ClerkUpload } from "./clerk-upload";
import { UploadForm } from "./upload-form";

export default async function UploadPage() {
  const base = apiUrl();
  if (clerkEnabled()) {
    await auth.protect();
    return (
      <main>
        <p className="kicker">Detection</p>
        <h1>Upload</h1>
        <p className="lede">Signed-in requests send a Clerk session token to {base}.</p>
        <ClerkUpload apiUrl={base} />
      </main>
    );
  }

  if (process.env.NEXT_PUBLIC_AUTH_MODE === "dev") {
    return (
      <main>
        <p className="kicker">Local only</p>
        <h1>Upload</h1>
        <p className="lede">
          This workstation sends the dev credential. The API is running with
          AUTH_MODE=dev. That mode stays off public hosts.
        </p>
        <UploadForm apiUrl={base} token="dev" />
      </main>
    );
  }

  return <AuthGate title="Upload" />;
}
