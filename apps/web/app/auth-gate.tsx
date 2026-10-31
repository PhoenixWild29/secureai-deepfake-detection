export function AuthGate({ title }: { title: string }) {
  return (
    <main>
      <p className="kicker">Auth required</p>
      <h1>{title}</h1>
      <div className="card">
        <p>This page calls the API after sign-in is configured.</p>
        <p>
          For Clerk, set <code>NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY</code> and{" "}
          <code>CLERK_SECRET_KEY</code> here, and <code>CLERK_ISSUER</code> on the
          API. A public API also sets <code>CLERK_AUTHORIZED_PARTIES</code> to this
          site&apos;s origin so the <code>azp</code> claim is checked.
        </p>
        <p>
          A private workstation can set <code>NEXT_PUBLIC_AUTH_MODE=dev</code> here
          and <code>AUTH_MODE=dev</code> on the API. That mode stays off public hosts.
        </p>
      </div>
    </main>
  );
}
