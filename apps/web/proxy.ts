import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Phase 0 auth placeholder (Next.js proxy, the successor to middleware).
 *
 * TODO(phase-1): replace this body with Clerk `clerkMiddleware()` from
 * `@clerk/nextjs` and protect product routes. Do not add secrets here.
 * Requests pass through until then.
 */
export function proxy(request: NextRequest) {
  return NextResponse.next({
    request: {
      headers: request.headers,
    },
  });
}

export const config = {
  matcher: ["/upload/:path*"],
};
