import { auth } from "@clerk/nextjs/server";
import { ClerkUpload } from "./clerk-upload";
import { UploadForm } from "./upload-form";

function clerkEnabled(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && process.env.CLERK_SECRET_KEY);
}

export default async function UploadPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  if (clerkEnabled()) {
    await auth.protect();
    return (
      <main>
        <p className="kicker">Detection</p>
        <h1>Upload</h1>
        <p className="lede">Signed-in requests send a Clerk session token to {apiUrl}.</p>
        <ClerkUpload apiUrl={apiUrl} />
      </main>
    );
  }

  if (process.env.NEXT_PUBLIC_AUTH_MODE === "dev") {
    return (
      <main>
        <p className="kicker">Local only</p>
        <h1>Upload</h1>
        <p className="lede">
          This workstation sends the dev credential. The API must be running with
          AUTH_MODE=dev. Do not use this on a public host.
        </p>
        <UploadForm apiUrl={apiUrl} token="dev" />
      </main>
    );
  }

  return (
    <main>
      <p className="kicker">Auth required</p>
      <h1>Upload</h1>
      <p className="lede">
        Job routes require a Clerk JWT. Set NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and
        CLERK_SECRET_KEY, and set CLERK_ISSUER on the API. On a private
        workstation you can set NEXT_PUBLIC_AUTH_MODE=dev here and AUTH_MODE=dev
        on the API instead. This page does not call the API until one of those
        is configured.
      </p>
    </main>
  );
}
