# Vercel (Guardian)

The Next.js app lives in `apps/web`. Create one Vercel project for that directory. Do not point Vercel at the repository root or at this `deploy/vercel` folder.

| Setting | Value |
| --- | --- |
| Root directory | `apps/web` |
| Framework | Next.js |
| Install command | `npm install` |
| Build command | `npm run build` |

`apps/web/vercel.json` sets `"framework": "nextjs"`.

## Environment variables

Set these in the Vercel project. Do not commit values. The app builds with the Clerk keys empty. `/upload` then tells the visitor that a Clerk JWT is required and does not call the API.

| Name | Notes |
| --- | --- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk frontend key |
| `CLERK_SECRET_KEY` | Server-only Clerk secret |
| `NEXT_PUBLIC_CLERK_SIGN_IN_URL` | `/sign-in` |
| `NEXT_PUBLIC_CLERK_SIGN_UP_URL` | `/sign-up` |
| `NEXT_PUBLIC_API_URL` | Public Railway API origin, no trailing path |

`NEXT_PUBLIC_AUTH_MODE=dev` is a private-workstation switch. Do not set it on the Vercel project. The API must not use `AUTH_MODE=dev` in production either.

On the API, set `CORS_ORIGINS` to this site's origin. Do not use `CORS_ORIGINS=*`. The API rejects that value.

The API also needs `CLERK_ISSUER` and `CLERK_AUTHORIZED_PARTIES` including this site. An empty allow-list skips the `azp` check and is only for local Clerk. Those variables belong on the API, not in the web project. `GET /health` on the API reports `"auth":"clerk"` in that mode.

`/jobs` is the signed-in history page. `/jobs/{id}` is the report. The browser refreshes the Clerk session token while it polls.

No blockchain or Solana variables.
