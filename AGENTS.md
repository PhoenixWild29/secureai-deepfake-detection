# AGENTS.md

## Cursor Cloud specific instructions

### What to work on

New work is the rebuild on `main`: `apps/` and `packages/`. Route behavior, quotas, and billing rules are in `README.rebuild.md`.

The API on `main` already includes Clerk JWTs, Stripe test-mode billing, quotas, workspaces, outbound job webhooks, report attestation, PDF export, optional Sentry, admin health, and API keys.

The legacy Flask API (`api.py`, root `requirements.txt`, root `Dockerfile`) and the Vite app (`secureai-guardian/`) remain in this tree. Leave that code in place. Product changes go in the rebuild. `.github/workflows/ci.yml` and the other workflow files beside `rebuild.yml` still target that legacy tree (`tests/`, `api.py`, `secureai-guardian/`). They have no path filter, so they also run on rebuild pull requests. Judge the rebuild by `rebuild.yml`.

### Layout

| Path | Role |
| --- | --- |
| `apps/web` | Next.js Guardian. Dev server on port 3000. |
| `apps/api` | FastAPI. Dev server on port 8000. Clerk JWT, or `AUTH_MODE=dev` on a private workstation. |
| `apps/worker` | CPU worker. Same Redis queue and Postgres rows as the API. |
| `packages/detector` | `DETECTOR_MODE=cpu` heuristic, or `stub`. No GPU weights and no PyTorch. |
| `packages/shared` | Job models, Postgres store, Redis queue, object storage, report attestation. |

`deploy/local/docker-compose.yml` starts local Redis, Postgres, and optional MinIO. `deploy/railway/README.md` and `deploy/vercel/README.md` are config notes. This repo does not contain a live SecureAI Railway or Vercel project. Do not invent deploy URLs, and do not commit secrets.

### Services

Postgres and Redis have to be running before the API or worker, and before the integration tests that CI refuses to skip.

```bash
docker run --rm -p 6379:6379 redis:7-alpine
docker run --rm -p 5432:5432 \
  -e POSTGRES_USER=secureai \
  -e POSTGRES_PASSWORD=secureai \
  -e POSTGRES_DB=secureai \
  postgres:16-alpine
```

`deploy/local/docker-compose.yml` starts the same two services. Its MinIO service is only for `STORAGE_BACKEND=s3`. The local default is filesystem storage. `MEDIA_ROOT` is an absolute path shared by the API and the worker (`mkdir -p /var/lib/secureai/media`). A relative path points at different directories after `cd apps/api`.

Copy `apps/api/.env.example` to `apps/api/.env` and export it in the shells below. Do not commit a filled-in copy.

GPU, Solana, Celery, and the legacy ensemble weights are outside this product.

### Run locally

Packages declare `requires-python >=3.11`. Rebuild CI and both Dockerfiles use Python 3.12. Create the venv with `python3`: this environment has no `python` on `PATH` until the venv is active.

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r apps/api/requirements-dev.txt
python -m pip install -e packages/shared -e packages/detector
python -m pip install -e apps/worker --no-deps
export AUTH_MODE=dev
export DEV_AUTH_SUBJECT=user_dev
export DATABASE_URL=postgresql+psycopg://secureai:secureai@127.0.0.1:5432/secureai
export REDIS_URL=redis://127.0.0.1:6379/0
export STORAGE_BACKEND=filesystem
export MEDIA_ROOT=/var/lib/secureai/media
export CORS_ORIGINS=http://localhost:3000
mkdir -p "$MEDIA_ROOT"
cd apps/api
uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
```

`create_app` runs `alembic upgrade head` on startup. Importing `app.main` does not connect. Health check: `curl http://localhost:8000/health` (public; body includes `"auth":"dev"` or `"auth":"clerk"`).

Worker, same virtualenv and the same `DATABASE_URL`, `REDIS_URL`, and storage settings, from the repository root after the API has migrated once:

```bash
python -m worker
```

`python -m worker --once` scores one job and exits. `python -m worker --demo --once` generates a clip, stores it, and scores it. The worker image runs `python -m worker` as PID 1. SIGTERM finishes the job already popped and the webhook POST already in progress. `deploy/railway/worker.railway.json` waits 75 seconds before SIGKILL. `DETECTOR_MODE` defaults to `cpu`. `DETECTOR_MODE=stub` hashes the path and does not open the file. `apps/worker/pyproject.toml` marks dependencies dynamic; the editable install above passes `--no-deps` so pip does not install `packages/shared` and `packages/detector` a second time. `pip install ./apps/worker` (what CI does) installs both.

Web app. Node.js 20.9 or newer. CI uses Node 22. `apps/web/package-lock.json` is committed.

```bash
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

Private workstation, matching the API bypass:

```bash
NEXT_PUBLIC_AUTH_MODE=dev NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

With Clerk keys empty and `NEXT_PUBLIC_AUTH_MODE` unset, `/upload`, `/jobs`, and a report page do not call the API. `npm run lint` and `npm run build` succeed with those keys empty. Before editing Next.js APIs, read `apps/web/AGENTS.md` and the guides in `apps/web/node_modules/next/dist/docs/`.

### Lint, tests, and CI

Workflow: `.github/workflows/rebuild.yml` (pull requests, and pushes to `main` and `master`).

| Job | What it runs |
| --- | --- |
| `web` | Working directory `apps/web`. Node 22, `npm ci`, `npm run lint`, `npm run build`. Typecheck is the Next.js build. There is no web test script. Timeout 20 minutes. |
| `api` | Python 3.12. Redis 7 and Postgres 16 service containers. `REQUIRE_SERVICES=1`. Installs `apps/api/requirements-dev.txt` and `./apps/worker`. System packages `libglib2.0-0` and `libgomp1` (OpenCV). Import check, then pytest below. Timeout 20 minutes. |
| `images` | Runs after `api` succeeds. Builds `apps/api/Dockerfile` and `apps/worker/Dockerfile` from the repository root. Does not log in and does not push. Timeout 30 minutes. |

Local pytest matches the API job. In-memory tests always run. Postgres and Redis cases skip when those services are down. `REQUIRE_SERVICES=1` turns that skip into a failure (CI sets it). S3 is a fake client in `packages/shared/tests/test_storage.py`; CI has no live bucket.

```bash
PYTHONPATH=apps/api python -m pytest \
  apps/api/tests packages/shared/tests packages/detector/tests apps/worker/tests -q
```

The import check from CI:

```bash
PYTHONPATH=apps/api python -c "from app.main import create_app; assert create_app.__name__ == 'create_app'"
```

`apps/api/requirements-dev.txt` pins `httpx2` because Starlette's TestClient imports `httpx2`. Keep that name.

Image builds, from the repository root:

```bash
docker build -f apps/api/Dockerfile -t secureai-api .
docker build -f apps/worker/Dockerfile -t secureai-worker .
```

`apps/api/Dockerfile.dockerignore` and `apps/worker/Dockerfile.dockerignore` replace the root `.dockerignore` for those builds, so the legacy model weights stay out of the context. A context of `apps/api` or `apps/worker` breaks the `packages/` copies. The repository-root `Dockerfile` is the legacy Flask image.

`.github/workflows/ci.yml` still matrices Python 3.9, 3.10, and 3.11 and runs `pytest tests/` for the legacy Flask tree. Rebuild packages require Python 3.11 or newer. `rebuild.yml` and both Dockerfiles use 3.12, which is the version to match.

### Migrations

Alembic scripts are `apps/api/alembic/versions/`. `apps/api/alembic.ini` is the config file; startup sets `script_location` to `apps/api/alembic`. Head revision is `20261101_0009` (job-list keyset indexes; `20261101_0008` is `api_keys`, SHA-256 hashes only). Chain: `20261031_0001` through `20261101_0009`.

From `apps/api`, with Postgres up:

```bash
DATABASE_URL=postgresql+psycopg://secureai:secureai@127.0.0.1:5432/secureai alembic upgrade head
```

Start the API before the worker the first time. The worker reads rows; it does not run Alembic.

### Environment names

Values stay out of git. The names in this section are non-exhaustive. `apps/api/.env.example` is the source of truth for API variables, including quota, seat, rate-limit, timeout, and attempt keys. Web placeholders are in `apps/web/.env.example`.

Clerk, API: `AUTH_MODE` (default `clerk`; `dev` accepts only `Authorization: Bearer dev` and is a private-workstation bypass), `CLERK_ISSUER`, `CLERK_JWKS_URL` (optional), `CLERK_AUTHORIZED_PARTIES`, `DEV_AUTH_SUBJECT`. The API refuses to start in clerk mode until `CLERK_ISSUER` is set. An empty `CLERK_AUTHORIZED_PARTIES` skips the `azp` check and is only for local Clerk.

Clerk, web: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`, `NEXT_PUBLIC_CLERK_SIGN_IN_URL`, `NEXT_PUBLIC_CLERK_SIGN_UP_URL`, `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_AUTH_MODE` (leave unset on any public host).

Stripe test mode, API only: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_PRO`, `STRIPE_PRICE_TEAM`, `PUBLIC_APP_URL`, `QUOTA_MODE`. Empty `STRIPE_SECRET_KEY` disables Checkout. Do not put Stripe secrets on the web app.

Shared runtime: `DATABASE_URL` (driver `postgresql+psycopg://`), `REDIS_URL`, `QUEUE_BACKEND`, `QUEUE_KEY` (default `secureai:jobs`; API and worker must match), `STORAGE_BACKEND`, `MEDIA_ROOT`, `S3_BUCKET`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_ENDPOINT`, `S3_REGION`, `S3_AUTO_CREATE_BUCKET` (leave false outside MinIO), `CORS_ORIGINS` (explicit origins; the API rejects `*`), `DETECTOR_MODE`, `ATTESTATION_PRIVATE_KEY`, `ATTESTATION_KEY_ID`, `SENTRY_DSN`, `SENTRY_ENVIRONMENT`, `SENTRY_RELEASE`, `ADMIN_USER_IDS`.

### Deploy notes

When a project is created later: Guardian is a Vercel project with root directory `apps/web` (install `npm install`, build `npm run build`). API and worker are Railway services whose root directory is the repository root, Dockerfiles `apps/api/Dockerfile` and `apps/worker/Dockerfile`, API healthcheck `GET /health`. A deployed product needs Postgres, Redis, and object storage. Follow `deploy/vercel/README.md` and `deploy/railway/README.md`. No project URL is stored in this repo.
