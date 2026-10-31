export default async function SignUpPage() {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return (
      <main>
        <h1>Sign up</h1>
        <p className="lede">
          Add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and CLERK_SECRET_KEY to enable
          Clerk. A private workstation can use NEXT_PUBLIC_AUTH_MODE=dev with
          AUTH_MODE=dev on the API instead.
        </p>
      </main>
    );
  }
  const { SignUp } = await import("@clerk/nextjs");
  return (
    <main>
      <SignUp />
    </main>
  );
}
