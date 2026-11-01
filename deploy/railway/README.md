# Railway (rebuild API and worker)

Two CPU services. No GPU. No secrets in this repo. Do not provision them from this change.

The files `deploy/railway/api.railway.json` and `deploy/railway/worker.railway.json` are reference Config as Code. Railway does **not** load them automatically. They do not sit at the service root, and a service with no config path keeps building the repository-root `Dockerfile`, which is the legacy Flask image.

## Config as Code is closing

Railway is closing Config as Code to new services. The sunset is **2026-12-01**. After that, set the same values in the service settings UI. Do not also add `.railway/railway.ts`. One source of settings per service. `railway.toml` is not used.

Until the sunset, if you attach a config file, set the service **Config file path** explicitly:

| Service | Config file path | Dockerfile path |
| --- | --- | --- |
| `api` | `deploy/railway/api.railway.json` | `apps/api/Dockerfile` |
| `worker` | `deploy/railway/worker.railway.json` | `apps/worker/Dockerfile` |

Root directory for both services is the **repository root**. The Dockerfiles copy `packages/`. A root directory of `apps/api` or `apps/worker` breaks those copies.

In the service settings, set the builder to Dockerfile and the Dockerfile path to the table above. Leaving the Dockerfile path empty selects `/Dockerfile` and builds the legacy image.

After 2026-12-01, enter those same Dockerfile paths, the API healthcheck path `/health`, and the restart policy in the dashboard. The JSON files stay as the checklist.

Build locally from the repository root:

```bash
docker build -f apps/api/Dockerfile -t secureai-api .
docker build -f apps/worker/Dockerfile -t secureai-worker .
```

The API listens on `$PORT` (default 8000). The worker has no HTTP port. It BRPOPs the shared Redis list. It also delivers workspace webhooks from `{QUEUE_KEY}:webhooks` on a background thread, so detection does not wait on that HTTP call.

## Variables

Set these in Railway. Do not commit values. Do not set `AUTH_MODE=dev` on these services.

| Variable | Service | Value |
| --- | --- | --- |
| `PORT` | api | Injected by Railway |
| `AUTH_MODE` | api | `clerk` (the default). Required with `CLERK_ISSUER` |
| `CLERK_ISSUER` | api | Clerk Frontend API origin, no trailing slash |
| `CLERK_JWKS_URL` | api | Optional. Defaults to `{CLERK_ISSUER}/.well-known/jwks.json` |
| `CLERK_AUTHORIZED_PARTIES` | api | Comma-separated allowed `azp` values, including the Vercel origin. Required on a public API. Empty skips `azp` and is only for local Clerk |
| `DATABASE_URL` | api, worker | Postgres URL using the `postgresql+psycopg://` driver |
| `REDIS_URL` | api, worker | Shared Redis instance |
| `QUEUE_BACKEND` | api, worker | `redis` (the default) |
| `QUEUE_KEY` | api, worker | Optional. Default `secureai:jobs`. Both services must match |
| `STORAGE_BACKEND` | api, worker | `s3` for a Railway bucket, MinIO, or R2 |
| `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | api, worker | Bucket credentials |
| `S3_ENDPOINT` | api, worker | Railway or other S3-compatible endpoint. Empty for AWS |
| `S3_REGION` | api, worker | Optional. Default `us-east-1` |
| `S3_AUTO_CREATE_BUCKET` | api, worker | Leave unset or `false` in production. `true` is for MinIO/local only |
| `DETECTOR_TIMEOUT_SECONDS` | worker | Optional. Default `60`. Hard stop around `detect_video` |
| `STUCK_JOB_SECONDS` | worker | Optional. Default `180`. Must be greater than the detector timeout |
| `JOB_MAX_ATTEMPTS` | worker | Optional. Default `3` |
| `RATE_LIMIT_JOBS` | api | Optional. Default `30` per window. `0` disables |
| `RATE_LIMIT_UPLOADS` | api | Optional. Default `60` per window. `0` disables |
| `RATE_LIMIT_WINDOW_SECONDS` | api | Optional. Default `60` |
| `RATE_LIMIT_ATTESTATIONS` | api | Optional. Default `60` public verify and key reads per window. `0` disables |
| `RATE_LIMIT_API_KEYS` | api | Optional. Default `10` API key creates per window per user. `0` disables |
| `ATTESTATION_PRIVATE_KEY` | api | Unencrypted PKCS8 Ed25519 PEM. Empty disables attestation (503). Do not commit it |
| `ATTESTATION_KEY_ID` | api | Optional key label. Default `v1`. Change it when you rotate the private key |
| `MEDIA_ROOT` | api, worker | Only for `STORAGE_BACKEND=filesystem`. Use the same absolute path on both |
| `CORS_ORIGINS` | api | Explicit Guardian origins, comma-separated. The API rejects `*` |
| `DETECTOR_MODE` | worker | `cpu` (the default). `stub` does not read the file |
| `STRIPE_SECRET_KEY` | api | Stripe test or live secret. Empty disables Checkout and, with `AUTH_MODE=clerk`, leaves callers on the free trial |
| `STRIPE_WEBHOOK_SECRET` | api | Signing secret for `POST /v1/billing/webhook` |
| `STRIPE_PRICE_PRO` | api | Recurring Price id for Pro |
| `STRIPE_PRICE_TEAM` | api | Optional recurring Price id for Team |
| `PUBLIC_APP_URL` | api | Guardian origin, no trailing slash. Checkout and portal return here |
| `QUOTA_MODE` | api | Optional `enforce` or `unlimited` |
| `WEBHOOK_MAX_ATTEMPTS` | worker | Optional. Default `5`, maximum `10` |
| `WEBHOOK_TIMEOUT_SECONDS` | worker | Optional. Default `10`, maximum `30` |
| `SENTRY_DSN` | api, worker | Optional. Empty disables Sentry. Set it on each service that should report |
| `SENTRY_ENVIRONMENT` | api, worker | Optional label such as `production`. Empty uses the SDK default `production` when `AUTH_MODE` is not `dev` |
| `SENTRY_RELEASE` | api, worker | Optional release name. The SDK reads this env var when it is set |
| `ADMIN_USER_IDS` | api | Comma-separated Clerk user ids for `GET /v1/admin/health`. Empty allows nobody |

API startup runs `alembic upgrade head`. Revision `20261101_0008` creates `api_keys` (SHA-256 hashes only). No new required variable. Pro and Team callers mint keys with `POST /v1/api-keys`; Free is 402.

The platform healthcheck stays `GET /health`. `GET /v1/admin/health` needs a Clerk session whose `sub` is in `ADMIN_USER_IDS`. It reports Postgres, Redis, and object storage and returns 503 when one of them is down. Do not use it as the Railway healthcheck. A failing dependency would restart the API, and the route is not public. The response has no credentials, bucket name, or exception text.

`CORS_ORIGINS=*` is not a safe production value. Job routes send `Authorization`, and the process exits if that wildcard is set.

Start the API before the worker the first time. The API runs Alembic. The worker only reads and updates rows.

Solana is out of scope. Report attestation is an API signature, not a chain anchor.
