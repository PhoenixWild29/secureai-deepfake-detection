# SecureAI rebuild (Phase 0)

The legacy Flask API (`api.py`), React Guardian (`secureai-guardian/`), and the rest of the existing tree stay where they are. Treat them as reference only while the saleable product is rebuilt under `apps/` and `packages/`. Nothing in this scaffold deletes or moves that code.

Source for review is `main`. This repository has no `master` branch.

## Layout

```
apps/web/             Next.js App Router Guardian shell
apps/api/             FastAPI: GET /health, POST /v1/jobs, GET /v1/jobs/{id}
apps/worker/          CPU worker that consumes the same in-memory job stub
packages/detector/    detect_video() CPU stub (no weights, no GPU)
packages/shared/      Job models and the Phase 0 queue
deploy/railway/       Service config for api + worker
deploy/vercel/        Notes for the apps/web Vercel project
```

Postgres, Redis, and object storage are required in the new design. Phase 0 does not connect them. `QUEUE_BACKEND=memory` (the default) keeps jobs inside one process. `QUEUE_BACKEND=redis` raises `NotImplementedError` on purpose.

TODO(phase-1): one Redis queue shared by the API and the worker, Postgres for job rows, object storage for video bytes, Clerk on the web app, and Clerk JWT checks on the API. Solana stays deferred. Do not add it here.

The legacy `deploy/nginx.conf` is untouched. New deploy notes live in `deploy/railway/` and `deploy/vercel/`.

## Run the API

From the repository root, with Python 3.11+:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r apps/api/requirements-dev.txt
python -m pip install -e packages/shared -e packages/detector -e apps/worker
cd apps/api
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Expected body: `{"status":"ok","service":"secureai-api"}`.

Queue a metadata stub (no video bytes):

```bash
curl -s -X POST http://localhost:8000/v1/jobs \
  -H 'Content-Type: application/json' \
  -d '{"filename":"clip.mp4","content_type":"video/mp4","byte_size":128}'
```

Auth is a placeholder. `Authorization` is ignored and requests are accepted. Phase 1 verifies Clerk JWTs.

`CORS_ORIGINS` defaults to `http://localhost:3000`.

## Run the worker

In another shell, with the same virtualenv:

```bash
python -m worker --demo --once
```

That enqueues a synthetic job on **this process's** memory queue, calls `detect_video`, and exits. A long-running poll is:

```bash
python -m worker
```

It will not see jobs created by the API until Phase 1 connects Redis.

## Run the web app

Node.js 20.9 or newer:

```bash
cd apps/web
cp .env.example .env.local   # optional; Clerk keys can stay empty
npm install
npm run dev
```

Open `http://localhost:3000`. The home page says **SecureAI Guardian (rebuild)**. `/upload` posts filename metadata to `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`) and does not upload the file.

```bash
npm run lint
npm run build
```

## Tests

```bash
PYTHONPATH=apps/api python -m pytest \
  apps/api/tests packages/shared/tests packages/detector/tests apps/worker/tests -q
```

CI for this scaffold is `.github/workflows/rebuild.yml`. It does not need secrets. The older workflows still cover the legacy tree.
