# SecureAI rebuild (Phase 4)

The legacy Flask API (`api.py`), React Guardian (`secureai-guardian/`), and the repository-root `Dockerfile` stay in place. The saleable product lives under `apps/` and `packages/`.

Source for review is `main`.

## Layout

```
apps/web/             Next.js Guardian. Uploads a video, polls a job, lists history, shows a report, downloads JSON, and opens billing.
apps/api/             FastAPI. Clerk JWT (or a private dev bypass), Postgres, Redis.
apps/worker/          CPU worker. Same Redis queue and Postgres rows as the API.
packages/detector/    DETECTOR_MODE=cpu scores texture, motion, temporal stability, and a face or skin-region cue. DETECTOR_MODE=stub hashes the path.
packages/shared/      Job models, Postgres store, Redis queue, object storage.
deploy/railway/       Reference service settings. Not auto-loaded. See that README.
deploy/vercel/        Notes for the apps/web Vercel project.
deploy/local/         Optional Redis, Postgres, and MinIO compose file.
```

Postgres holds job rows. Redis holds job ids (`QUEUE_KEY`, default `secureai:jobs`) plus an in-flight lease at `{QUEUE_KEY}:inflight`. Object storage holds the bytes. A filename alone is not the media.

A worker that dies after Redis pops an id keeps that id in the lease. The pop and the lease write are one Lua script, so a crash cannot drop an id that has left the list but was not leased. A blocking worker uses `BLMOVE` of the list onto itself only to wait; that does not remove the id. Each loop, the worker sweeps leases older than `STUCK_JOB_SECONDS` (default 180, and it must be greater than `DETECTOR_TIMEOUT_SECONDS`). The sweep claims a stale lease and republishes that id in one script, and only when the attempt it read is still the stored attempt. The job row is released back to `queued` only when its attempt still matches, so a slow worker cannot release a newer claim. The job is requeued until `JOB_MAX_ATTEMPTS` (default 3), then marked failed with `Detection failed.` If `claim` or `fail` raises, the worker puts the id back or marks the row failed, then exits so the process supervisor restarts it. The id is not left only in the lease. Ack and renew compare the attempt from the pop that this worker made.

`detect_video` runs in a child process. If it exceeds `DETECTOR_TIMEOUT_SECONDS` (default 60), the worker stops that process and fails the job with the same fixed detail. The traceback stays in the log.

## Auth

Job routes are not public. `GET /health` is public and reports `auth` as `clerk` or `dev`.

`AUTH_MODE` defaults to `clerk`. The API refuses to start until `CLERK_ISSUER` is set to the Clerk Frontend API origin, for example `https://<slug>.clerk.accounts.dev`. The API loads JWKS from `CLERK_JWKS_URL` or `{CLERK_ISSUER}/.well-known/jwks.json`, checks RS256, `exp`, `iss`, and `sub`, and refreshes JWKS once when the token `kid` is not in the cache.

`CLERK_AUTHORIZED_PARTIES` is a comma-separated list of allowed `azp` values (the Guardian origin). When the list is non-empty, a token whose `azp` is missing or not in the list is rejected. When the list is empty, the API skips the `azp` check and logs a warning. An empty list is only for local Clerk. A public API sets the list, and `GET /health` reports `"auth":"clerk"` in that mode.

The web app asks Clerk for a session token on every poll. Session tokens last about a minute, and a detection can run longer than that.

`AUTH_MODE=dev` accepts only `Authorization: Bearer dev` and stamps `DEV_AUTH_SUBJECT` (default `user_dev`). It is a private-workstation bypass. Do not put it on a public host. Junk tokens are rejected in this mode too. Anonymous requests are rejected in both modes.

## CORS

`CORS_ORIGINS` defaults to `http://localhost:3000`. List explicit origins. The API rejects `CORS_ORIGINS=*` at startup because job routes send `Authorization`. A wildcard is not a production setting.

## Local services

Redis and Postgres have to be running before the API. Docker is one way:

```bash
docker run --rm -p 6379:6379 redis:7-alpine
docker run --rm -p 5432:5432 \
  -e POSTGRES_USER=secureai \
  -e POSTGRES_PASSWORD=secureai \
  -e POSTGRES_DB=secureai \
  postgres:16-alpine
```

`deploy/local/docker-compose.yml` starts the same two services plus an optional MinIO bucket. Filesystem storage is the local default, so MinIO is only needed when you set `STORAGE_BACKEND=s3`.

Copy `apps/api/.env.example` to `apps/api/.env` and export it in the shells below. Do not commit filled-in secrets.

## Run the API

From the repository root, with Python 3.11+:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r apps/api/requirements-dev.txt
python -m pip install -e packages/shared -e packages/detector
python -m pip install -e apps/worker --no-deps
export AUTH_MODE=dev
export DATABASE_URL=postgresql+psycopg://secureai:secureai@127.0.0.1:5432/secureai
export REDIS_URL=redis://127.0.0.1:6379/0
export STORAGE_BACKEND=filesystem
export MEDIA_ROOT=/var/lib/secureai/media
export CORS_ORIGINS=http://localhost:3000
cd apps/api
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

`MEDIA_ROOT` is an absolute path. The API command above runs with working directory `apps/api`. A relative `.media` would be `apps/api/.media` for the API and `./.media` for a worker started at the repo root, so the two processes would not see the same files. Create the directory first (`mkdir -p /var/lib/secureai/media`).

The factory migrates on startup (`alembic upgrade head`). Importing `app.main` does not connect. You can also migrate by hand:

```bash
cd apps/api
DATABASE_URL=postgresql+psycopg://secureai:secureai@127.0.0.1:5432/secureai alembic upgrade head
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected body includes `"auth":"dev"` or `"auth":"clerk"`. `POST /v1/jobs` without a bearer token returns 401.

Filesystem upload, then a job (dev mode):

```bash
curl -s -X POST http://localhost:8000/v1/media \
  -H 'Authorization: Bearer dev' \
  -F 'file=@clip.mp4;type=video/mp4'
curl -s -X POST http://localhost:8000/v1/jobs \
  -H 'Authorization: Bearer dev' \
  -H 'Content-Type: application/json' \
  -d '{"object_key":"<key from the upload>","filename":"clip.mp4","content_type":"video/mp4","byte_size":128}'
```

`POST /v1/uploads` returns `mode: direct` and `upload_url: /v1/media` for the filesystem backend. With `STORAGE_BACKEND=s3` it returns a presigned POST. The policy includes `content-length-range` from 1 byte through 50 MB, so a larger body is rejected by the bucket. Keys look like `media/<user>/<32 hex>.<suffix>`.

Job creation reads the object size and ETag from storage and stores those. The client-reported `byte_size` is not the size on the row. An empty object or one over 50 MB is rejected. If Redis rejects the id after the row insert, the API retries, then marks the row failed with `Could not queue the job.` and returns 503. That row stays at attempt 0 and does not count against the monthly quota. A job that fails during detection still counts. The row is not left `queued` with no id in Redis.

The quota check and the insert share a lock on the billing account row, or on the organization row when `X-Org-Id` is set (`SELECT … FOR UPDATE` on Postgres). Two concurrent `POST /v1/jobs` calls cannot both pass the cap.

Before the worker scores a file, it reads the size and ETag again. A rewrite after the job was accepted fails the job instead of being scored. The S3 download sends `IfMatch` with that ETag, so a rewrite between the head check and the GET is not saved or scored. A failed S3 download deletes its temp file. A job row with no ETag cannot send `IfMatch`.

`POST /v1/uploads`, `POST /v1/media`, and `POST /v1/jobs` are rate limited per caller. Defaults are 60 uploads and 30 jobs per 60 seconds (`RATE_LIMIT_UPLOADS`, `RATE_LIMIT_JOBS`, `RATE_LIMIT_WINDOW_SECONDS`). `0` disables that bucket. With `QUEUE_BACKEND=redis` the counters live in Redis. A limited request returns 429 and `Too many requests`.

`GET /v1/jobs` lists the caller's jobs, newest first.

S3 settings, when you use them: `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, optional `S3_ENDPOINT` (MinIO or Railway), `S3_REGION`. `S3_AUTO_CREATE_BUCKET` defaults to false. The API and worker do not call `CreateBucket` unless you set `S3_AUTO_CREATE_BUCKET=true`, which is for MinIO or another local bucket only.

## Run the worker

Start the API once so the schema exists, then in another shell with the same virtualenv and the same `DATABASE_URL`, `REDIS_URL`, and storage settings:

```bash
python -m worker
```

One job, then exit:

```bash
python -m worker --once
```

Generate a tiny clip, store it, and score it (needs Redis, Postgres, and the schema):

```bash
python -m worker --demo --once
```

`DETECTOR_MODE` defaults to `cpu`. That path samples frames and mixes four signals: texture (Laplacian energy), motion (frame-to-frame change), temporal instability (histogram disagreement and uneven motion), and a region cue. The region cue uses OpenCV's bundled Haar cascade when that file is present, and otherwise a skin-tone blob. It rises when the seam around that region is much sharper than the interior. No region scores 0, which means there was no cue. The mix is a fixed formula. It does not download weights and it does not use a GPU.

This is not a measured deepfake detector. It has no published accuracy on a labeled benchmark. High-frequency noise and hard cutouts can look synthetic. A careful fake can look real. A score is not legal evidence and not a guarantee. Do not quote an accuracy percentage for this model.

`DETECTOR_MODE=stub` hashes the path and does not open the file. Use it for tests. Failed jobs store the fixed detail `Detection failed.` A completed CPU job stores a short JSON note in `detail` (`v`, `model` `cpu-multisignal-v1`, and the four signals). The traceback stays in the worker log. `DETECTOR_TIMEOUT_SECONDS` bounds each `detect_video` call. `STUCK_JOB_SECONDS` and `JOB_MAX_ATTEMPTS` bound crash recovery.

`apps/worker/pyproject.toml` marks dependencies as dynamic. `apps/worker/setup.py` points them at `packages/shared` and `packages/detector`, so a clean `pip install ./apps/worker` installs both and the worker imports. The editable checkout command above passes `--no-deps` so pip does not try to install those same paths a second time.

## Run the web app

Node.js 20.9 or newer:

```bash
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`. With Clerk keys empty and `NEXT_PUBLIC_AUTH_MODE` unset, `/upload`, `/jobs`, and a report page explain how to configure Clerk or the private dev bypass, and they do not call the API. `/jobs` lists the current user's jobs. `/jobs/{id}` shows prediction, confidence, status, detail, and timestamps, and keeps checking while the job is still queued or processing. A completed report can show the four CPU signals and download JSON. PDF is not available yet. `/docs`, `/privacy`, and `/terms` are public. `/.well-known/security.txt` is a static file. The upload page shows progress (`Uploading…`, `Waiting for a worker…`, `Scoring the video…`) and, after about three minutes, links to the report instead of stopping at fifteen seconds.

Private workstation, matching the API dev bypass:

```bash
NEXT_PUBLIC_AUTH_MODE=dev NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

With `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` and `CLERK_SECRET_KEY` set, `/upload` requires a Clerk session and sends that session token to the API. `proxy.ts` returns `NextResponse.next()` when those keys are absent. It does not copy caller headers onto the request.

```bash
npm run lint
npm run build
```

Both succeed with Clerk keys empty.

## Tests

```bash
PYTHONPATH=apps/api python -m pytest \
  apps/api/tests packages/shared/tests packages/detector/tests apps/worker/tests -q
```

The end-to-end test uploads a generated clip, runs `python -m worker --once`, and expects a completed job. It skips when Redis or Postgres is down. Set `REQUIRE_SERVICES=1` to fail instead of skip. The rebuild workflow sets that, because those services are part of the job. S3 is exercised with a fake client in `packages/shared/tests/test_storage.py` (presigned `content-length-range`, bucket auto-create off, temp-file cleanup). There is no live bucket in CI.

CI is `.github/workflows/rebuild.yml`. It starts Redis and Postgres service containers and runs those tests. It does not build Docker images yet. The older workflows still cover the legacy tree.

`apps/api/requirements-dev.txt` pins `httpx2` because Starlette's TestClient imports `httpx2`. That name is intentional.

## Billing and workspaces

Plans are Free trial, Pro, and Team. Free trial is 10 jobs per month. Pro is 500. Team is 2,000 for the workspace. A free workspace has 3 seats. A Team workspace has 25. Override them with `QUOTA_FREE`, `QUOTA_PRO`, `QUOTA_TEAM`, `SEAT_LIMIT_FREE`, and `SEAT_LIMIT_TEAM`.

A job counts when it is created, including jobs that later fail during detection. A job that never reached Redis (`Could not queue the job.`, attempt 0) does not count. The window is the Stripe subscription period when that period is current, otherwise the UTC calendar month. Personal jobs use the user plan. Jobs sent with `X-Org-Id` use the workspace plan and show up for every member. The count and the insert hold the account or organization row lock, so concurrent creates cannot overshoot the cap.

`POST /v1/jobs` returns **402** when a free-trial caller is over the cap, with `detail` telling them to upgrade. A Pro or Team caller who is over the included amount gets **403**. Uploads stay on the short rate limit. The monthly cap is the job.

`GET /v1/billing` returns the plan, status, jobs used, jobs remaining (`jobs_limit`), the period, and the caller's workspaces. `jobs_limit` is null when quotas are unlimited.

`POST /v1/billing/checkout` with `{"plan":"pro"}` opens Stripe Checkout for the personal account. `{"plan":"team","org_id":"org_..."}` does the same for a workspace the caller owns. `POST /v1/billing/portal` opens the Customer Portal. Both return `{url}` when a new Checkout session is allowed. If that account or workspace already has a subscription in `active`, `trialing`, or `past_due`, checkout returns **409** and `detail` telling the caller to open the billing portal. It does not create a second subscription. `canceled` and `unpaid` may start a new Checkout. Guardian's Billing page sends the browser to the returned URL, and it shows `detail` when checkout is refused.

`POST /v1/billing/webhook` accepts `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.paid`, and `invoice.payment_failed`. It checks `Stripe-Signature` with `STRIPE_WEBHOOK_SECRET`. There is no Clerk token on that route. A bad signature is 400. The handler stores `stripe_customer_id`, `stripe_subscription_id`, subscription status, plan, the current period, and the Stripe event `created` time on the user or the organization. Event ids are stored once.

Events are not applied in arrival order. A subscription update, delete, or invoice is ignored when its event `created` time is older than the one already stored, or when `current_period_end` is older and the event has no `created` time. The same subscription id is not moved from a terminal status (`canceled`, `unpaid`, `incomplete_expired`) back to an entitled status by an event that is not newer. A delete, update, or invoice whose subscription id is not the stored `stripe_subscription_id` does not change the account. Only a newer `checkout.session.completed` may replace that id. That is what stops a late `customer.subscription.updated` after `deleted` from restoring a plan, and what stops an old subscription's delete from wiping a replacement Checkout.

Paid plans are taken from `STRIPE_PRICE_PRO` and `STRIPE_PRICE_TEAM` only. An unknown price id does not fall back to `metadata.plan` and does not upgrade the account. Checkout still records the plan it was created with; the following subscription event corrects it when the price id is one of those two.

`past_due` keeps the paid plan for the dunning window. This API does not expire `past_due` by itself. Stripe billing settings must end dunning in `unpaid` or `canceled` (Smart Retries, then cancel or mark the subscription unpaid). Those terminal statuses return the account to the free trial. `canceled` does that as well. An unpaid Checkout session does not grant Pro or Team.

A Team workspace that moves to the free plan is clamped to `SEAT_LIMIT_FREE`. The newest non-owner members are removed until the seat count fits. The owner stays. The workspace is not left with more members than the free plan allows.

Clerk Organizations are not used. A workspace is a row in Postgres. `POST /v1/orgs` creates one and makes the caller the owner. `POST /v1/orgs/{id}/members` adds a Clerk user id. The owner cannot be removed. Guardian keeps the selected workspace in the browser and sends `X-Org-Id` on history, reports, new jobs, and billing.

### Stripe environment

Set these on the API. Do not commit values. Test mode first (`sk_test_...`, `whsec_...`, `price_...`).

| Variable | Purpose |
| --- | --- |
| `STRIPE_SECRET_KEY` | Secret key for Checkout, Customer Portal, and Customer create |
| `STRIPE_WEBHOOK_SECRET` | Signing secret for `POST /v1/billing/webhook` |
| `STRIPE_PRICE_PRO` | Recurring Price id for Pro |
| `STRIPE_PRICE_TEAM` | Recurring Price id for Team. Omit it to hide Team checkout |
| `PUBLIC_APP_URL` | Guardian origin, no trailing slash. Default `http://localhost:3000`. Success, cancel, and portal return URLs are under `/billing` |
| `QUOTA_MODE` | `enforce` or `unlimited`. Default: `unlimited` when `AUTH_MODE=dev` and `STRIPE_SECRET_KEY` is empty; otherwise `enforce` |

Empty `STRIPE_SECRET_KEY` disables Checkout and the portal (HTTP 503, `Billing is not configured`). In `AUTH_MODE=dev` the API logs a warning and does not enforce quotas, so local job flow keeps working. Set `QUOTA_MODE=enforce` to apply the free trial on that workstation. `AUTH_MODE=clerk` without a Stripe key stays on the free trial and logs that Checkout is disabled. A missing `STRIPE_WEBHOOK_SECRET` while the secret key is set logs that subscription updates cannot be verified.

### Test-mode walkthrough

In the Stripe dashboard (test mode), create two recurring prices and copy the price ids. Point a webhook at `https://<api-host>/v1/billing/webhook` for the five events above, or forward locally:

```bash
stripe listen --forward-to localhost:8000/v1/billing/webhook
```

Put the printed `whsec_...` in `STRIPE_WEBHOOK_SECRET`. Use card `4242 4242 4242 4242` in Checkout. Then:

```bash
curl -s http://localhost:8000/v1/billing -H 'Authorization: Bearer dev'
curl -s -X POST http://localhost:8000/v1/billing/checkout \
  -H 'Authorization: Bearer dev' \
  -H 'Content-Type: application/json' \
  -d '{"plan":"pro"}'
```

The checkout response is a Stripe URL. After the webhook, `GET /v1/billing` shows `"plan":"pro"`. Open Guardian at `/billing` to see the remaining quota, create a workspace, and use Upgrade or Manage billing.

The API tests sign fixture events with a test webhook secret and replace Checkout calls. They do not contact Stripe.

## Batch jobs and report export

`POST /v1/jobs/batch` accepts `{"items":[...]}` with 1 to 10 objects. Each item has the same fields as `POST /v1/jobs` (`object_key`, `filename`, and optional `content_type` / `byte_size`). The caller and `X-Org-Id` match a single create. The jobs rate limit is charged once per item after the items validate. A duplicate key, a missing object, or a foreign key returns 400 and does not spend that limit. The monthly quota uses the same plan window and lock as `POST /v1/jobs`. The rows for one batch are inserted in one transaction. The response is `202` and `{"jobs":[...]}`. If the queue accepts some ids and then rejects one, `jobs` lists only the ids that were queued. The rest are failed with `Could not queue the job.` and do not count toward the cap.

```bash
curl -s -X POST http://localhost:8000/v1/jobs/batch \
  -H 'Authorization: Bearer dev' \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"object_key":"<key>","filename":"clip.mp4","content_type":"video/mp4"}]}'
```

`GET /v1/jobs/{id}/report` returns JSON for a completed job: prediction, confidence, model, signals, and a limitations string. The body is also `Content-Disposition: attachment`. A job that is still queued, processing, or failed returns 409. Guardian's report page shows the signals and downloads that JSON.

PDF is not implemented. TODO: render the same payload to PDF when a small dependency is worth adding. `pdf_available` is false until then.

Pro API keys are not issued. TODO: mint scoped keys for Pro and Team. Until then, job routes use the Clerk session token (or `Bearer dev` on a private workstation).

Outbound completion webhooks are deferred. A per-user or per-org URL plus HMAC would need a new table, a secret, and a worker POST.

Public pages: `/docs` (how detection works and its limits), `/privacy`, `/terms`, and `/.well-known/security.txt`.

## Still later

The legacy GPU ensemble and Docker image builds in CI. Solana stays deferred. The legacy Flask tree stays in the repo.
