# SecureAI rebuild (Phase 4)

The legacy Flask API (`api.py`), React Guardian (`secureai-guardian/`), and the repository-root `Dockerfile` stay in place. The saleable product lives under `apps/` and `packages/`.

Source for review is `main`.

## Layout

```
apps/web/             Next.js Guardian. Uploads a video, polls a job, lists history, shows a report, downloads JSON, a PDF, and a signed attestation, opens billing, and sets a workspace webhook.
apps/api/             FastAPI. Clerk JWT (or a private dev bypass), Postgres, Redis.
apps/worker/          CPU worker. Same Redis queue and Postgres rows as the API. A background thread delivers webhooks.
packages/detector/    DETECTOR_MODE=cpu scores texture, motion, temporal stability, and a face or skin-region cue. DETECTOR_MODE=stub hashes the path.
packages/shared/      Job models, Postgres store, Redis queue, object storage, report attestation.
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

`AUTH_MODE=dev` accepts `Authorization: Bearer dev` and stamps `DEV_AUTH_SUBJECT` (default `user_dev`). It is a private-workstation bypass. Do not put it on a public host. Junk tokens are rejected in this mode too. Anonymous requests are rejected in both modes. A `sai_` bearer is an API key in clerk mode and in dev mode. See the API keys section below.

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

Open `http://localhost:3000`. With Clerk keys empty and `NEXT_PUBLIC_AUTH_MODE` unset, `/upload`, `/jobs`, and a report page explain how to configure Clerk or the private dev bypass, and they do not call the API. `/jobs` lists the current user's jobs. `/jobs/{id}` shows prediction, confidence, status, detail, and timestamps, and keeps checking while the job is still queued or processing. A completed report can show the four CPU signals, download JSON, download a PDF, and download a signed attestation when the API has a key. `/docs`, `/privacy`, and `/terms` are public. `/.well-known/security.txt` is a static file. The upload page shows progress (`Uploading…`, `Waiting for a worker…`, `Scoring the video…`) and, after about three minutes, links to the report instead of stopping at fifteen seconds.

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

Events are not applied in arrival order. A subscription update, delete, or invoice is ignored when its event `created` time is older than the one already stored, or when `current_period_end` is older and the event has no `created` time. The same subscription id is not moved from a terminal status (`canceled`, `unpaid`, `incomplete_expired`) back to an entitled status by an event that is not newer. `invoice.paid` and `invoice.payment_failed` do not move a terminal status at all, even when that invoice is newer than the delete or the unpaid update. A delete, update, or invoice whose subscription id is not the stored `stripe_subscription_id` does not change the account. Only a newer `checkout.session.completed` may replace that id. That is what stops a late `customer.subscription.updated` after `deleted` from restoring a plan, what stops a late invoice from turning `canceled` into `active` or `past_due` (which would make Checkout return 409), and what stops an old subscription's delete from wiping a replacement Checkout.

Paid plans are taken from `STRIPE_PRICE_PRO` and `STRIPE_PRICE_TEAM` only. Checkout reads a line-item price id when the event has one. When it does not, Checkout uses the plan recorded for that session at creation, and only if that session's price id is still one of those two. `metadata.plan` is not read. An unknown price id does not upgrade the account. A later subscription event corrects the plan when its price id is one of those two. A paid session that cannot be named is logged at error, because the customer may already have been charged.

That recorded plan lives in `checkout_intents`. Rows older than 7 days are deleted when another Checkout session is saved or a Stripe event is applied, including an event id that was already stored. Stripe retries a webhook for about 3 days, so a late `checkout.session.completed` with no price id can still find its row. There is no migration for this cleanup.

`past_due` keeps the paid plan for the dunning window. This API does not expire `past_due` by itself. Stripe billing settings must end dunning in `unpaid` or `canceled` (Smart Retries, then cancel or mark the subscription unpaid). Those terminal statuses return the account to the free trial. `canceled` does that as well. Leave Smart Retries on that ending state before any live key is considered. An unpaid Checkout session does not grant Pro or Team.

A Team workspace that moves to the free plan is clamped to `SEAT_LIMIT_FREE`. The newest non-owner memberships are hard-deleted until the seat count fits. The owner stays. A later upgrade does not restore the removed members. The workspace is not left with more members than the free plan allows.

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

`POST /v1/jobs/batch` accepts `{"items":[...]}` with 1 to 10 objects. Each item has the same fields as `POST /v1/jobs` (`object_key`, `filename`, and optional `content_type` / `byte_size`). The caller and `X-Org-Id` match a single create. The jobs rate limit is charged once per item after the items validate. A duplicate key, a missing object, or a foreign key returns 400 and does not spend that limit. The monthly quota uses the same plan window and lock as `POST /v1/jobs`. The rows for one batch are inserted in one transaction. A full success is `202` and `{"jobs":[...],"failed":[]}`. If the queue accepts some ids and then rejects one, the response stays `202`. `jobs` lists the ids that were queued. `failed` lists the rest, each with `id`, the zero-based `index` in `items`, and `detail` `Could not queue the job.` Those rows do not count toward the cap. If the queue rejects the first id, nothing is queued and the response is `503` with that same detail.

```bash
curl -s -X POST http://localhost:8000/v1/jobs/batch \
  -H 'Authorization: Bearer dev' \
  -H 'Content-Type: application/json' \
  -d '{"items":[{"object_key":"<key>","filename":"clip.mp4","content_type":"video/mp4"}]}'
```

`GET /v1/jobs/{id}/report` returns JSON for a completed job: prediction, confidence, model, signals, and a limitations string. The body is also `Content-Disposition: attachment`. A job that is still queued, processing, or failed returns 409. `pdf_available` is true. That flag means this API can render a PDF. It does not mean the caller's plan is entitled to download one. Guardian's report page shows the signals and downloads that JSON.

`GET /v1/jobs/{id}/report.pdf` returns the same completed job as `application/pdf` with `Content-Disposition: attachment; filename="<job id>.pdf"`. The page is titled SecureAI Detection Report. It includes the job id, organization id when the job has one (`n/a` for a personal job), file name, status, prediction, confidence, model, signals, created and updated timestamps, and the same limitations text as the JSON report. It is not legal evidence. A job that is not complete returns 409. A missing session is 401. A job the caller cannot read is 404, the same as the JSON report.

PDF uses the same plan rule as attestation. Pro and Team can download. The plan is the workspace plan when `X-Org-Id` is set, and the personal plan otherwise. `past_due` still counts as paid. A free plan is 402 with `PDF export requires a Pro or Team plan.` `AUTH_MODE=dev` with `QUOTA_MODE=unlimited` (the workstation default when Stripe is unset) can download on the free plan. `AUTH_MODE=clerk` always requires Pro or Team, including when `QUOTA_MODE=unlimited`.

The renderer is [fpdf2](https://pypi.org/project/fpdf2/) 2.9.0, pinned in `apps/api/requirements.txt`. It writes text with the built-in Helvetica font (Windows-1252) and does not launch a browser. Characters outside Windows-1252 are replaced with `?`. The PDF lists at most 12 signals and says when more were stored.

```bash
curl -s http://localhost:8000/v1/jobs/job_.../report.pdf \
  -H 'Authorization: Bearer dev' \
  -o report.pdf
```

Guardian's completed report page puts Download PDF next to the JSON and the attestation. If that route returns 409 or 404, the page hides the PDF button and keeps the rest of the report. A plan rejection (402) shows the error and disables the PDF button so it cannot be clicked again.

## Report attestation

Phase 4c signs a completed report with Ed25519. It is not Solana and not a chain anchor. The signature shows that this API's attestation key issued one canonical JSON payload. It does not show that the clip is real or synthetic, and it is not legal evidence. The detector limitations in the payload are the same text as the JSON report.

Set `ATTESTATION_PRIVATE_KEY` to an unencrypted PKCS8 Ed25519 PEM. A one-line env value may use `\n` between the PEM lines. `ATTESTATION_KEY_ID` defaults to `v1`. Change that id when you rotate the key. The API loads one key. After the private key or the id changes, attestations signed with the previous `key_id` stop verifying, including when the verifier omits `key_id`. `GET /v1/attestations/keys` returns only the current public key. Re-issue anything that still needs to verify. If the private key is unset, `POST /v1/jobs/{id}/attest`, `POST /v1/attestations/verify`, and `GET /v1/attestations/keys` return 503 with `Attestation is not configured`.

Generate a key for a private workstation and do not commit it:

```bash
python -c 'from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey; from cryptography.hazmat.primitives import serialization; print(Ed25519PrivateKey.generate().private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode().replace(chr(10), "\\n"))'
```

Put that single line in `ATTESTATION_PRIVATE_KEY`.

Issuing uses the same caller and `X-Org-Id` rules as the JSON report. A queued, processing, or failed job is 409. Pro and Team can issue. The plan is the workspace plan when `X-Org-Id` is set, and the personal plan otherwise. `past_due` still counts as paid. A free plan is 402 with `Attestation requires a Pro or Team plan.` `AUTH_MODE=dev` with `QUOTA_MODE=unlimited` (the workstation default when Stripe is unset) can issue on the free plan. `AUTH_MODE=clerk` always requires Pro or Team, including when `QUOTA_MODE=unlimited`.

```bash
curl -s -X POST http://localhost:8000/v1/jobs/job_.../attest \
  -H 'Authorization: Bearer dev' \
  -o attestation.json
```

The response is the verify body. `payload` is a string of compact JSON, not a nested object. The signature is standard base64 over those exact UTF-8 bytes. `algorithm` is `Ed25519`. The same payload and key return the stored signature. The row is `job_attestations` (`job_id`, `key_id`, `signature`, `created_at`).

Verify does not use Clerk. `RATE_LIMIT_ATTESTATIONS` defaults to 60 per window. The key is the TCP peer (`request.client.host`). The API does not read `X-Forwarded-For`. Behind Railway, or any other reverse proxy, that peer is the proxy, so every caller shares one window. Trusting the header would let a client pick a new key on each request. `0` disables the limit. The process is not started with proxy headers.

```bash
curl -s -X POST http://localhost:8000/v1/attestations/verify \
  -H 'Content-Type: application/json' \
  --data-binary @attestation.json
curl -s http://localhost:8000/v1/attestations/keys
```

A matching signature returns `{"valid":true,"key_id":"v1","algorithm":"Ed25519","public_key":"-----BEGIN PUBLIC KEY-----\\n..."}`. A wrong signature, a wrong `key_id`, or a payload that was parsed and encoded again returns `{"valid":false}`. Check the public key from `GET /v1/attestations/keys` or from a valid verify response. Do not trust a key that arrived only inside an email attachment.

Guardian's report page downloads `job_<id>.attestation.json`, shows the signature, and links to `/docs#attestation`. If the API returns 503, the page keeps the JSON download and shows a short note that attestation is not available.

Pro and Team API keys authenticate job routes without a Clerk browser session. Mint one with a session (`Bearer dev` on a private workstation, or a Clerk JWT). The response includes `secret` once. Later responses list `prefix` only. Postgres stores SHA-256 in `api_keys.secret_hash` (`20261101_0008`). The API runs `alembic upgrade head` on startup.

```bash
curl -s -X POST http://localhost:8000/v1/api-keys \
  -H 'Authorization: Bearer dev' \
  -H 'Content-Type: application/json' \
  -d '{"name":"laptop"}'
curl -s http://localhost:8000/v1/jobs/job_.../report \
  -H 'Authorization: Bearer sai_...'
curl -s -X DELETE http://localhost:8000/v1/api-keys/key_... \
  -H 'Authorization: Bearer dev'
```

A free plan is 402 with `API keys require a Pro or Team plan.` That includes `AUTH_MODE=dev` with `QUOTA_MODE=unlimited`. `past_due` still counts as paid. The plan is the workspace plan when the request has `X-Org-Id` or the key is bound to a workspace, and the personal plan otherwise. A personal Pro key sent as a Free workspace is 402. Send `X-Org-Id` to mint a workspace key; the caller must be an owner or admin, and the workspace plan must be Pro or Team. A workspace key is limited to that org. It keeps working only while its minter is still an owner or admin. Removal or demotion to member revokes it on the next use (401), and promoting that person later does not restore the secret. Revoke is immediate. Unknown and revoked secrets are 401. An API key cannot mint another key, and it cannot call `GET /v1/admin/health` (404, same as a signed-in non-admin). Anonymous callers of that route still get 401. `RATE_LIMIT_API_KEYS` defaults to 10 creates per window per user (`0` disables). Each scope can hold 25 live keys. On Postgres, creates for one scope take a transaction advisory lock so two workers cannot both pass that cap. Guardian's `/keys` page follows the workspace selected in the header.

Clerk session checks are unchanged. `AUTH_MODE=dev` still accepts only `Bearer dev` plus `sai_` keys. Other bearers are rejected.

Public pages: `/docs` (how detection works and its limits), `/privacy`, `/terms`, and `/.well-known/security.txt`.

## Webhooks

Phase 4 sends one workspace's terminal jobs to a single HTTPS URL. Personal jobs (no `X-Org-Id`) do not fire. Stripe billing webhooks are a different route and are unchanged.

The owner or an admin registers the URL. Any member of that workspace can read it. A caller who is not a member gets 403, and the response does not include another workspace's URL. The signing secret is write-only: `GET` returns `secret_set`, never the secret. The secret is stored in plaintext in Postgres so the worker can sign. Restrict database access the same way as `STRIPE_WEBHOOK_SECRET`.

```bash
curl -s -X PUT http://localhost:8000/v1/orgs/org_.../webhook \
  -H 'Authorization: Bearer dev' \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com/hooks/secureai","secret":"replace-with-16-plus-chars","notify_failures":true}'
curl -s http://localhost:8000/v1/orgs/org_.../webhook \
  -H 'Authorization: Bearer dev'
curl -s http://localhost:8000/v1/orgs/org_.../webhook/deliveries \
  -H 'Authorization: Bearer dev'
curl -s -X DELETE http://localhost:8000/v1/orgs/org_.../webhook \
  -H 'Authorization: Bearer dev'
```

`PUT` replaces the URL. Omit `secret` to keep the current one. Send `"secret":""` to clear it. A new secret must be 16 to 256 characters. Omit `notify_failures` on an update to keep the current choice. A new endpoint defaults to sending failures. Set `notify_failures` to false to send only `completed`. The URL must be `https`, with no userinfo and no private or loopback host. Guardian's `/webhooks` page edits the workspace selected in the header.

When a job reaches `completed` or `failed`, the API or the worker inserts one delivery row and publishes its id. That publish is a Redis `ZADD` (or the in-memory queue in tests). It does not open a socket. The long-running worker (`python -m worker`) posts from a background thread, so a slow receiver does not sit on the detection loop. `python -m worker --once` enqueues and exits; a long-running worker delivers later. The Redis key is `{QUEUE_KEY}:webhooks` (default `secureai:jobs:webhooks`). The API and the worker must use the same `QUEUE_KEY`.

The body is compact JSON, the same bytes on every retry:

```json
{"confidence":0.5,"job_id":"job_...","org_id":"org_...","prediction":"fake","status":"completed","timestamp":"2026-11-01T12:00:00+00:00"}
```

`timestamp` is the job's `updated_at` in UTC. `prediction` and `confidence` are null when the job failed. Headers are `Content-Type: application/json` and `User-Agent: SecureAI-Webhooks/1`. Redirects are not followed. The certificate must validate. The worker resolves the hostname once and tries those addresses in order, stopping at the first TCP connection that succeeds. The Host header and the certificate name stay the hostname, so a DNS answer that changes after the check cannot point that connection at a private address. Any TCP port is still accepted. A public address that proxies somewhere else is outside this check. Two owners saving the endpoint at the same time: the second write updates the row instead of failing the request.

When a secret is set, the worker also sends:

```
X-SecureAI-Timestamp: 1761998400
X-SecureAI-Signature: t=1761998400,v1=<hex hmac sha256 of "{timestamp}.{raw body}">
```

The timestamp in the signature is the unix time of that attempt, not the `timestamp` field in the JSON. Compare with `hmac.compare_digest`. A missing secret means those two headers are omitted.

A non-2xx response or a network error stays `pending` and is retried. The waits are 2s, 8s, 32s, 128s, then 300s. `WEBHOOK_MAX_ATTEMPTS` defaults to 5 (maximum 10). The next try after the cap is not sent. The row stores `attempt`, `last_status_code`, and a short `last_error`. `GET /v1/orgs/{id}/webhook` includes `last_delivery`. `GET .../webhook/deliveries` lists the latest 20. Delivery is at-least-once: a crash after the POST and before the row update can send the same body again. `WEBHOOK_TIMEOUT_SECONDS` defaults to 10 (maximum 30).

`WEBHOOK_MAX_ATTEMPTS` and `WEBHOOK_TIMEOUT_SECONDS` are read by the worker. Empty values use the defaults.

## Errors and admin health

`SENTRY_DSN` turns on Sentry for the API and the worker. Leave it empty and neither process imports the SDK or sends events. Set the same DSN on both Railway services, or only on the one you want to watch. `SENTRY_ENVIRONMENT` labels the event (`production`, `staging`, `development`). When it is empty, a dev workstation (`AUTH_MODE=dev`) is labeled `development` and a Clerk deploy is labeled `production` by the SDK. `SENTRY_RELEASE` is optional. The SDK reads it when it is set.

Events do not include auth headers, cookies, request bodies, or local variables. A database or Redis URL in an exception message is sent with the userinfo replaced. Do not put media bytes or secrets into log messages. The API captures unhandled exceptions. The worker captures `ERROR` logs, which is how a failed job is already recorded. Default integrations are off, so the SDK does not flush on exit. The worker calls `flush` for up to 2 seconds before it exits, including after a configuration failure or `--once`. No new variable controls that wait.

`GET /health` stays public and shallow (`status`, `service`, `auth`). Railway's healthcheck stays on `/health`. Do not point it at the admin route. A down dependency must not restart the API, and that route requires a session.

`GET /v1/admin/health` requires `Authorization: Bearer <session>` and a subject listed in `ADMIN_USER_IDS` (comma-separated Clerk user ids, the same `sub` the API already stores). An empty list allows nobody. A missing or invalid session is 401. A signed-in caller who is not on the list, including an API key whose subject is listed, is 404 `Not Found` with no dependency details. That matches an unknown path. An allowlisted session gets Postgres, Redis, and object storage as `ok` or `error`, plus `storage_backend` (`filesystem` or `s3`). `200` means all three answered. `503` means the caller is an admin and at least one did not. The body has no URL, bucket, key, or exception text. The S3 probe is `HeadBucket`. On AWS that call requires `s3:ListBucket`. A key that can `PutObject` but cannot list the bucket reports storage as `error` while uploads still work. The filesystem probe creates and deletes a dotfile under `MEDIA_ROOT`.

Local dev, with the API on port 8000 and `ADMIN_USER_IDS` including `DEV_AUTH_SUBJECT`:

```bash
curl -s http://localhost:8000/health
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8000/v1/admin/health
curl -s -H 'Authorization: Bearer dev' http://localhost:8000/v1/admin/health
```

There is no Guardian admin page. Call the route with a Clerk session token.

## Still later

The legacy GPU ensemble and Docker image builds in CI. Solana stays deferred. Signed attestation does not replace that. The legacy Flask tree stays in the repo.
