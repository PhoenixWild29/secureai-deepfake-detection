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

The API listens on `$PORT` (default 8000). The worker has no HTTP port. It BRPOPs the shared Redis list.

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
| `MEDIA_ROOT` | api, worker | Only for `STORAGE_BACKEND=filesystem`. Use the same absolute path on both |
| `CORS_ORIGINS` | api | Explicit Guardian origins, comma-separated. The API rejects `*` |
| `DETECTOR_MODE` | worker | `cpu` (the default). `stub` does not read the file |

`CORS_ORIGINS=*` is not a safe production value. Job routes send `Authorization`, and the process exits if that wildcard is set.

Start the API before the worker the first time. The API runs Alembic. The worker only reads and updates rows.

Solana is out of scope.
