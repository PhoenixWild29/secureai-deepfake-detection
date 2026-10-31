# Railway (Phase 0 stubs)

Two CPU services. No GPU. No secrets in this repo. Postgres, Redis, and object storage are part of the product design and are **not** provisioned here.

These files are service-level Config as Code (`railway.json` shape). They are not a project graph. Do not also add `.railway/railway.ts` for the same services until a Railway project exists; each service should have one config model. When a project is linked, prefer one TypeScript project file and retire these manifests instead of owning the services twice.

`railway.toml` is intentionally not used.

## Service settings

Set the Railway **root directory** to the repository root for both services so the Dockerfiles can copy `packages/`. Paths inside the JSON files are relative to that root.

| Service | Config-as-code path | Dockerfile |
| --- | --- | --- |
| `api` | `deploy/railway/api.railway.json` | `apps/api/Dockerfile` |
| `worker` | `deploy/railway/worker.railway.json` | `apps/worker/Dockerfile` |

Build locally:

```bash
docker build -f apps/api/Dockerfile -t secureai-api .
docker build -f apps/worker/Dockerfile -t secureai-worker .
```

The API listens on `$PORT` (default 8000) and serves `GET /health`. The worker process polls; it has no HTTP port.

## Variables

Set these in Railway. Do not commit values.

| Variable | Service | Phase 0 |
| --- | --- | --- |
| `PORT` | api | Injected by Railway |
| `QUEUE_BACKEND` | api, worker | `memory` (default). `redis` fails on purpose |
| `CORS_ORIGINS` | api | Comma-separated Guardian origins, e.g. the Vercel URL |
| `REDIS_URL` | api, worker | Reserved. Unread until Phase 1 |
| `DATABASE_URL` | api | Reserved for Postgres job rows |
| `S3_ENDPOINT`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | api, worker | Reserved for Railway object storage |

Phase 1 adds Postgres, Redis, and a bucket to the project, then points `QUEUE_BACKEND` at Redis. Clerk JWT verification uses Clerk's JWKS on the API; the publishable key stays on Vercel, not here.

Solana is out of scope.
