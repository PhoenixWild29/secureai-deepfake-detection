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

After 2026-12-01, enter those same Dockerfile paths, the API healthcheck path `/health`, the API healthcheck timeout 60, the API drain 25, the worker drain 75, and the restart policy in the dashboard. Do not set a worker healthcheck path. The JSON files stay as the checklist.

Build locally from the repository root:

```bash
docker build -f apps/api/Dockerfile -t secureai-api .
docker build -f apps/worker/Dockerfile -t secureai-worker .
```

The API listens on `$PORT` (default 8000). `apps/api/docker_entrypoint.py` replaces the process with uvicorn, so the server is PID 1. SIGTERM stops new connections and drains in-flight requests for up to 20 seconds. `api.railway.json` sets `drainingSeconds` to 25 and `healthcheckTimeout` to 60 so Railway waits past that drain and the image healthcheck's 40 second start period. Keep `python docker_entrypoint.py` as the start command so that signal reaches uvicorn.

The worker has no HTTP port. It BRPOPs the shared Redis list. It also delivers workspace webhooks from `{QUEUE_KEY}:webhooks` on a background thread, so detection does not wait on that HTTP call. The image starts `python -m worker` as PID 1. That process handles SIGTERM: it stops taking new ids, finishes the job it already popped, and waits for the webhook POST already in progress so that delivery row is written before exit. The wait is twice `WEBHOOK_TIMEOUT_SECONDS` plus 2 seconds. The next due id stays on the queue. `python -m worker --once` scores one job and exits, which stops webhook delivery. Do not wrap the start command in a shell. Do not set a healthcheck path. The process does not listen, so a path would fail and the restart policy would cycle it.

`worker.railway.json` sets `drainingSeconds` to 75. That is the default poll (5 seconds) plus the default detector timeout (60 seconds) plus the Sentry flush (2 seconds) plus 8 seconds. The webhook join stays out of that sum: the POST runs while a popped job is scored. An idle SIGTERM spends the current poll, then the webhook join, then the 2 second Sentry flush. The maximum `WEBHOOK_TIMEOUT_SECONDS` of 30 keeps that idle shutdown inside 75 seconds. SIGTERM during the Redis wait does not cancel that wait, and an id popped before the flag is checked is still scored. A shorter drain SIGKILLs the worker and leaves that id leased until `STUCK_JOB_SECONDS` (default 180). A POST still open when the drain ends keeps its delivery lease (`WEBHOOK_TIMEOUT_SECONDS` + 15 seconds) and the next worker sends it. If you raise `DETECTOR_TIMEOUT_SECONDS` above 60, raise `drainingSeconds` by the same amount. The worker logs that warning once at startup and includes the delta. There is no `healthcheckTimeout` on this service.

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
| `DETECTOR_TIMEOUT_SECONDS` | worker | Optional. Default `60`. Hard stop around `detect_video`. Raising it means raising `drainingSeconds` by the same amount. The worker warns once at startup when it is above 60 |
| `STUCK_JOB_SECONDS` | worker | Optional. Default `180`. Must be greater than the detector timeout |
| `JOB_MAX_ATTEMPTS` | worker | Optional. Default `3` |
| `RATE_LIMIT_JOBS` | api | Optional. Default `30` per window. `0` disables |
| `RATE_LIMIT_UPLOADS` | api | Optional. Default `60` per window. `0` disables |
| `RATE_LIMIT_WINDOW_SECONDS` | api | Optional. Default `60` |
| `RATE_LIMIT_ATTESTATIONS` | api | Optional. Default `60` public verify and key reads per window, keyed by the TCP peer. `0` disables. `X-Forwarded-For` is not trusted, so a reverse proxy shares one window |
| `RATE_LIMIT_API_KEYS` | api | Optional. Default `10` API key creates per window per user. `0` disables |
| `ATTESTATION_PRIVATE_KEY` | api | Unencrypted PKCS8 Ed25519 PEM. Empty disables attestation (503). Do not commit it |
| `ATTESTATION_KEY_ID` | api | Optional key label. Default `v1`. Change it with the private key. Previous key ids stop verifying; only the current key is loaded |
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
| `WEBHOOK_TIMEOUT_SECONDS` | worker | Optional. Default `10`, maximum `30`. Shutdown waits up to twice this value plus 2 seconds for the POST already started |
| `SENTRY_DSN` | api, worker | Optional. Empty disables Sentry. Set it on each service that should report |
| `SENTRY_ENVIRONMENT` | api, worker | Optional label such as `production`. Empty uses the SDK default `production` when `AUTH_MODE` is not `dev` |
| `SENTRY_RELEASE` | api, worker | Optional release name. The SDK reads this env var when it is set |
| `ADMIN_USER_IDS` | api | Comma-separated Clerk user ids for `GET /v1/admin/health`. Empty allows nobody |

API startup runs `alembic upgrade head`. Revision `20261101_0008` creates `api_keys` (SHA-256 hashes only). No new required variable. Pro and Team callers mint keys with `POST /v1/api-keys`; Free is 402. A workspace key whose minter is removed or demoted is hard-revoked on the next use (401). Promoting that person later does not restore the secret.

The platform healthcheck stays `GET /health`. The API image `HEALTHCHECK` calls that same path after a 40 second start period, so Alembic can finish before failures count, and a runtime that reads the Dockerfile uses the same route. `GET /v1/admin/health` needs a Clerk session, or `Bearer dev` on a private workstation, whose subject is in `ADMIN_USER_IDS`. An API key is 404 even when that subject is listed, the same as any other signed-in non-admin. Anonymous callers are 401. The route reports Postgres, Redis, and object storage and returns 503 when one of them is down. Do not use it as the Railway healthcheck. A failing dependency would restart the API, and the route is not public. The response has no credentials, bucket name, or exception text. The S3 probe is `HeadBucket`, which AWS authorizes as `s3:ListBucket`. A key that can write objects but cannot list the bucket shows storage as `error` while uploads still succeed.

The worker flushes Sentry for up to 2 seconds before it exits. Leave `SENTRY_DSN` empty to send nothing. No extra variable is required.

Workspace webhook delivery tries each public address from one resolution, in order, and keeps the hostname for TLS. Signing secrets are stored in plaintext in `webhook_endpoints`. Any HTTPS port is accepted. `RATE_LIMIT_ATTESTATIONS` uses the TCP peer, not `X-Forwarded-For`. After an attestation key rotation, old `key_id` values no longer verify.

`CORS_ORIGINS=*` is not a safe production value. Job routes send `Authorization`, and the process exits if that wildcard is set.

Start the API before the worker the first time. The API runs Alembic. The worker only reads and updates rows.

Solana is out of scope. Report attestation is an API signature, not a chain anchor.
