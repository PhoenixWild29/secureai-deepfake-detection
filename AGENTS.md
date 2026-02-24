# AGENTS.md

## Cursor Cloud specific instructions

### Repository overview

SecureAI DeepFake Detection — a multi-service deepfake detection platform. The **master** branch contains all source code (the `main` branch has only docs).

| Service | Tech | Port | Start command |
|---------|------|------|---------------|
| Flask API backend | Python 3.11+ / Flask | 5000 | `python3 api.py` |
| SecureAI Guardian frontend | React 19 / Vite | 3000 | `cd secureai-guardian && npm run dev` |

Optional services (not required for local dev): PostgreSQL, Redis, Celery workers, Solana validator. The app gracefully degrades to file-based storage and skips blockchain when those are absent.

### Starting the backend

```bash
export USE_NNPACK=0
export USE_LOCAL_STORAGE=true
export LOG_DIR=/workspace/logs
mkdir -p uploads results logs run
python3 api.py
```

The first video analysis request triggers model loading (2-4 min on CPU). Subsequent requests are ~10-20 seconds. Health check: `curl http://localhost:5000/api/health`.

### Starting the frontend

```bash
cd secureai-guardian
npm install   # only if node_modules is missing
npm run dev   # Vite dev server on port 3000, proxies /api to localhost:5000
```

### Linting

- **Frontend**: `cd secureai-guardian && npx eslint . --ext .ts,.tsx` (requires ESLint 8 — the `.eslintrc.json` uses legacy config format)
- **Markdown**: `markdownlint '**/*.md'`

### Testing

- **Python API tests**: `python3 -m pytest tests/test_api_endpoints.py -v` (backend must be running)
- **Frontend tests**: `cd secureai-guardian && npm test` (no tests configured yet)
- **Full test suite**: `python3 tests/test_runner.py` (requires test data)

### Gotchas

- Use `python3` not `python` — the VM does not have a `python` symlink.
- The `~/.local/bin` directory must be on PATH for pip-installed CLI tools (celery, gunicorn, etc.).
- CPU-only PyTorch: install with `pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision torchaudio` **before** `pip install -r requirements.txt` to avoid pulling massive CUDA wheels.
- The secureai-guardian `package-lock.json` is committed; always use `npm install` (not `npm ci` which may fail on lockfile mismatches).
- ESLint in secureai-guardian uses `.eslintrc.json` (legacy format), so ESLint 8.x is required. ESLint 9+ will fail.
- The `gunicorn_config.py` writes logs to `/app/logs` (Docker path); for local dev, set `LOG_DIR=/workspace/logs` or run `python3 api.py` directly (which uses Flask's dev server).
