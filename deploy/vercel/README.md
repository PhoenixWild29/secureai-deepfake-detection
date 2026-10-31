# Vercel (Guardian)

The Next.js app lives in `apps/web`. Create one Vercel project for that directory. Do not point Vercel at the repository root or at this `deploy/vercel` folder.

| Setting | Value |
| --- | --- |
| Root directory | `apps/web` |
| Framework | Next.js |
| Install command | `npm install` |
| Build command | `npm run build` |

`apps/web/vercel.json` sets `"framework": "nextjs"`. This file is the reviewer note; Vercel reads the JSON next to the app.

## Environment variables

Set these in the Vercel project. Do not commit values. Phase 0 builds and runs with them empty; the upload page defaults the API URL to `http://localhost:8000`.

| Name | Notes |
| --- | --- |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Clerk frontend key. Unused until Phase 1 |
| `CLERK_SECRET_KEY` | Server-only. Unused until Phase 1 |
| `NEXT_PUBLIC_API_URL` | Public Railway API origin, no trailing path |

No blockchain or Solana variables.
