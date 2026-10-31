"use client";

import { SignInButton, UserButton, useAuth } from "@clerk/nextjs";

export function AuthButtons() {
  const { isSignedIn } = useAuth();
  if (isSignedIn) {
    return <UserButton />;
  }
  return <SignInButton mode="modal" />;
}
