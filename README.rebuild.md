# SecureAI rebuild (Phase 1)

The legacy Flask API (`api.py`), React Guardian (`secureai-guardian/`), and the repository-root `Dockerfile` stay in place. The saleable product lives under `apps/` and `packages/`.

Source for review is `main`.

## Layout

```
apps/web/             Next.js Guardian. Uploads a video and polls a job.
apps/api/             FastAPI. Clerk JWT (or a private dev bypass), Postgres, Redis.
apps/worker/          CPU worker. Same Redis queue and Postgres rows as the API.
packages/detector/    DETECTOR_MODE=cpu samples frames. DETECTOR_MODE=stub hashes the path.
packages/shared/      Job models, Postgres store, Redis queue, object storage.
deploy/railway/       Reference service settings. Not auto-loaded. See that README.
deploy/vercel/        Notes for the apps/web Vercel project.
deploy/local/         Optional Redis, Postgres, and MinIO compose file.
```

Postgres holds job rows. Redis holds job ids (`QUEUE_KEY`, default `secureai:jobs`). Object storage holds the bytes. A filename alone is not the media.

A worker that dies after Redis pops an id and before it finishes the row can leave that job `queued` or `processing` with nobody to retry it. Recovery is a later phase.

## Auth

Job routes are not public. `GET /health` is public and reports `auth` as `clerk` or `dev`.

`AUTH_MODE` defaults to `clerk`. The API refuses to start until `CLERK_ISSUER` is set to the Clerk Frontend API origin, for example `https://<slug>.clerk.accounts.dev`. The API loads JWKS from `CLERK_JWKS_URL` or `{CLERK_ISSUER}/.well-known/jwks.json`, checks RS256, `exp`, `iss`, and `sub`, and checks `azp` when `CLERK_AUTHORIZED_PARTIES` is non-empty. Set that list in any deployed environment.

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
export MEDIA_ROOT=.media
export CORS_ORIGINS=http://localhost:3000
cd apps/api
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

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

`POST /v1/uploads` returns `mode: direct` and `upload_url: /v1/media` for the filesystem backend. With `STORAGE_BACKEND=s3` it returns a presigned PUT URL and the object key. Keys look like `media/<user>/<32 hex>.<suffix>`.

S3 settings, when you use them: `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, optional `S3_ENDPOINT` (MinIO or Railway), `S3_REGION`.

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

`DETECTOR_MODE` defaults to `cpu` (OpenCV frame sample, no GPU, no downloaded weights). `DETECTOR_MODE=stub` hashes the path and does not open the file. Failed jobs store the fixed detail `Detection failed.` The traceback stays in the worker log.

`apps/worker/pyproject.toml` marks dependencies as dynamic. `apps/worker/setup.py` points them at `packages/shared` and `packages/detector`, so a clean `pip install ./apps/worker` installs both and the worker imports. The editable checkout command above passes `--no-deps` so pip does not try to install those same paths a second time.

## Run the web app

Node.js 20.9 or newer:

```bash
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`. With Clerk keys empty and `NEXT_PUBLIC_AUTH_MODE` unset, `/upload` explains that a JWT is required and does not call the API.

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

The end-to-end test skips when Redis or Postgres is down. It uploads a generated clip, runs `python -m worker --once`, and expects a completed job.

CI is `.github/workflows/rebuild.yml`. It starts Redis and Postgres service containers and runs those tests. It does not build Docker images yet. The older workflows still cover the legacy tree.

`apps/api/requirements-dev.txt` pins `httpx2` because Starlette's TestClient imports `httpx2`. That name is intentional.

## Still later

Guardian history and a richer account page, billing, the legacy ensemble, stuck-job recovery, production Clerk authorized parties on a real project, and Docker image builds in CI. Solana stays deferred.
