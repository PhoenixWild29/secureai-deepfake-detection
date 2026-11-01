import { clerkMiddleware } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";
import type { NextFetchEvent, NextRequest } from "next/server";

const clerk = clerkMiddleware();

/**
 * When Clerk keys are unset, pass the request through unchanged.
 * Do not copy caller headers onto the forwarded request.
 * When both keys are set, Clerk attaches the session for protected pages.
 */
export function proxy(request: NextRequest, event: NextFetchEvent) {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY || !process.env.CLERK_SECRET_KEY) {
    return NextResponse.next();
  }
  return clerk(request, event);
}

export const config = {
  matcher: [
    "/upload",
    "/upload/:path*",
    "/jobs",
    "/jobs/:path*",
    "/billing",
    "/billing/:path*",
    "/sign-in",
    "/sign-in/:path*",
    "/sign-up",
    "/sign-up/:path*",
  ],
};
