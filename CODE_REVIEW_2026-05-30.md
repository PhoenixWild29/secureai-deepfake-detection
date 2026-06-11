# SecureAI DeepFake Detection — Full Code Review

**Date:** 2026-05-30
**Reviewer:** Claude (Cowork)
**Scope:** Architecture, ML/model code, backend/API, security & infrastructure, frontend, tests. Reviewed the actual source across `ai_model/`, `api.py`, `app/`, `celery_app/`, `database/`, `utils/`, `storage/`, `monitoring/`, `secureai-guardian/`, `tests/`, Docker/nginx/systemd, and CI.

---

## TL;DR

This is an ambitious, feature-rich project with a lot of real engineering effort — production infra scaffolding, a React frontend, CI security tooling, Docker/nginx/TLS configs, and a few genuinely-trained models. But there is a **fundamental gap between what the README claims and what the running system actually does**, plus several **critical security issues**.

The three things that matter most:

1. **The live detection is not what the README sells.** The production inference path loads a ResNet trained for 1 epoch to a leakage-driven "100% accuracy" on *synthetic noise* fakes, blended with **untrained, random-weight** models and two components (CLIP, LAA-Net) that score at **chance (AUC ≈ 0.49)**. The README's headline "94.2% accuracy / 0.967 AUC" appears **nowhere** in the artifacts and exceeds the best real result by 4–7 points. Meanwhile the project's *own* legitimately-trained models (ResNet50 AUC 0.906, learned ensemble 0.927) are **dead code** the API never calls.
2. **Security holes that block any real deployment.** Live AWS keys + an X/Twitter session-cookie file sitting in the working tree; JWT secret defaulting to `'your-secret-key'`; core upload/detection endpoints with **no authentication**; an SSRF in URL analysis; a DB connection leak that exhausts the pool under load.
3. **Two half-merged backends and a green-by-construction CI** that can never fail. The codebase is mid-migration from a 2,680-line Flask monolith (`api.py`, marked deprecated but still present) to a FastAPI app (`app/`), with duplicated logic, conflicting docs, and a broken Celery pipeline.

None of this means the project is unsalvageable — the bones of a real product are here. But the priority right now should be **honesty + security + consolidation**, not new features.

---

## What's genuinely good (credit where due)

- **A few real, honestly-evaluated models.** `kaggle_training_code.py` is clean and methodologically sound (WeightedRandomSampler, AUC-based selection, frozen early layers). The resulting ResNet50 (test AUC **0.906**) and ConvNeXt (**0.915**) on Celeb-DF v2 are legitimate, and the saved results files even self-report overfitting — that's good scientific hygiene.
- **A learned logistic-regression ensemble** (`trained_models/ensemble_weights.json`, AUC **0.927**) that correctly learned to down-weight the useless components.
- **Thoughtful dependency CVE remediation** — `requirements.txt` has specific CVE/PVE IDs annotated per pin. The intent and tracking are genuinely good practice.
- **Solid TLS config** in nginx (TLS 1.2/1.3 only, modern ciphers, HSTS).
- **Non-root Docker user**, a properly-hardened `secureai-guardian.service` systemd unit.
- **Broad CI security tooling** (Bandit, Trivy, Gitleaks, TruffleHog, CodeQL, pip-audit) — coverage is real (enforcement is the problem, see below).
- **`tests/test_api_endpoints.py`** is a genuinely good, server-free FastAPI contract test suite.
- **Frontend keeps secrets server-side** — no API keys in the bundle; good error-handling/retry UX in `apiService.ts`.

---

## Critical findings

### C1 — Production detection uses leakage/untrained models; README benchmarks are fabricated
The API routes `enhanced`/`ensemble` requests (`ai_model/detect.py:79-99`) to `ensemble_detector.EnsembleDetector`, which loads ResNet from `ai_model/resnet_resnet50_best.pth` (`ensemble_detector.py:116-119`). Per `resnet_resnet50_metadata.json`, that checkpoint was trained for **1 epoch to `best_accuracy: 100.0`** on synthetic noise/blur fakes from `datasets/setup_training_data.py` (4 source videos, frame-level train/val leakage). The same ensemble also blends in:
- **CLIP** zero-shot prompt similarity — the project's own `trained_models/test_comparison.json` reports **AUC 0.499** (random).
- **LAA-Net** — **AUC 0.494** (random; it's fed raw frames instead of aligned face crops).
- **XceptionNet** (`xception_detector.py:62-64`) and **EfficientNet** (`efficientnet_detector.py:55`) — ImageNet backbones with **freshly random-initialized** 2-class heads, never trained on deepfakes. Xception even silently falls back to ResNet50 if the import fails.

The combiner uses *confidence-adaptive weighting* (`ensemble_detector.py:336-384`) where weight ∝ `|prob−0.5|` — i.e. it **rewards overconfident garbage** from the untrained models. The legitimately-trained models (`trained_models/resnet50_celeb_df_v2.pth`, ConvNeXt, FFT, learned weights) live only in `EnhancedDetector`, which the API **never invokes**.

The README's "94.2% accuracy / 0.967 AUC" and the per-model comparison table (LAA "91.8%", CLIP "89.5%") are **not substantiated anywhere** and are contradicted by the repo's own result files (best real ensemble = 0.927).

> **Impact:** users receive a confident-looking verdict that is, in practice, dominated by a leakage-trained model plus noise. For a product whose entire value proposition is *trustworthy* detection, this is the single most important issue. It is also a **misrepresentation risk** if these numbers are shown to customers or investors.

### C2 — "Security/AI" components that are theater
- `morpheus_security.py:300` returns `np.random.uniform(0.1, 0.9)` as an "anomaly score." The named threat patterns (rapid_face_changes, inconsistent_lighting, etc.) are declared but **never computed**.
- "Diffusion model awareness" (README claim) does not exist — it's the word "diffusion" inside a CLIP text prompt (`enhanced_detector.py:432`) plus an unused `--use_dm_aware` flag (`train_enhanced.py:591`).
- The frontend's "integrity signature" is `btoa('sig-${tier}-${historyLen}-v42-managed')` (`App.tsx:43`) — base64 of a public formula with no secret. Trivially forgeable; the tamper banner provides zero protection.

### C3 — Live secrets in the working tree
- `.env` holds a **real** AWS access key (`AKIA…`), a 41-char secret key, a real Sentry DSN, and a DB password. It is gitignored and **not in git history** (verified) — good — but these are live long-lived IAM credentials in a OneDrive-synced folder. **Rotate them** and move to an IAM role / secrets manager.
- `secrets/x_cookies.txt.txt` is a live X/Twitter session-cookie file (untracked, but bind-mounted into containers via `docker-compose.https.yml`). Treat as compromised; rotate the session.

### C4 — JWT secret defaults to a public string
`app/dependencies/auth.py:48`: `os.getenv('JWT_SECRET_KEY', 'your-secret-key')`. If the env var is unset, the HS256 signing key is a public literal → trivial token forgery. No startup check enforces a real value.

### C5 — Core endpoints have no authentication
- FastAPI `app/api/v1/endpoints/detect.py` — every detect route (`""`, `/url`, `/batch`) has **no `Depends(...)` auth** and no rate limiting.
- Flask `/api/analyze`, `/api/analyze-url`, `/api/batch`, `/api/sage/chat` — no auth. The `require_login()` decorator (`api.py:370`) is **defined but never applied**; auth is enforced only via ad-hoc `get_current_user()` checks on ~12 lesser endpoints.

> **Impact:** anyone can run expensive ML inference, drive the Gemini proxy (cost), or upload arbitrary files, unauthenticated.

### C6 — DB connection/session leak → pool exhaustion
`database/db_session.py:36` defines `get_db()` as a generator, but `api.py` consumes it as `db = next(get_db())` (e.g. `:623, 1261, 1340, 1913`). `next()` never drives the generator to its `finally`, so `db.close()` **never runs**. Over a `QueuePool(pool_size=10, max_overflow=20)`, this leaks a connection per request and exhausts the pool under load.

---

## High-severity findings

| # | Finding | Location |
|---|---------|----------|
| H1 | **SSRF** in URL analysis — no host allowlist / private-IP block; reachable from both apps (`169.254.169.254` metadata, internal services) | `utils/video_downloader.py:14-42, 246` |
| H2 | **Unbounded in-memory upload** in FastAPI (`await video.read()`) with no size limit → OOM DoS | `app/api/v1/endpoints/detect.py:197` |
| H3 | **Uploaded files never deleted** → disk exhaustion | `api.py:1106`, `detect.py:198` |
| H4 | **Broken Celery pipeline** — imports a missing `video_processing` package, so all heavy work runs blocking in-request; `training_tasks.py` has 11 `# TODO` DB-persistence stubs | `main.py:24`, `celery_app/tasks.py:24`, `training_tasks.py` |
| H5 | **Face detection initialized but never called** — detectors receive full frames, not aligned face crops (breaks LAA especially) | `enhanced_detector.py:400, 626-695` |
| H6 | **CORS `*` + `allow_credentials=True`** at both app and nginx layers, with `Authorization` allowed | `app/main.py:48`, `nginx.https.conf:126-134` |
| H7 | **Client-trusted subscription tier** — `userTier` read from `localStorage` and trusted; self-upgrade to `NEXUS` possible unless backend re-validates | `App.tsx:51,62` |
| H8 | **XSS in legacy UI** — unescaped filenames in `innerHTML` (live if the Flask `/` UI is still served) | `static/js/app.js:308,396` |
| H9 | **CI cannot fail** — every scan/test step is `|| exit 0` / `continue-on-error: true`, final gate `exit 0`; secret-scanning that would catch C3 can't block anything | `.github/workflows/{ci,security,deploy}.yml` |
| H10 | **No proxy rate limiting**; global `client_max_body_size 500M` + unauth analyze = trivial resource-exhaustion DoS | `nginx*.conf` |

---

## Medium-severity findings (selected)

- **Per-process global state breaks multi-worker** — `processing_stats`, `batch_results`, `_executor`, and a `SECRET_KEY` regenerated every process start (`api.py:271`) are inconsistent across gunicorn workers; sessions break across workers.
- **IDOR** — `/api/analytics/advanced` and `/api/user/stats` read *every* result file with no user filter (`api.py:2235-2244`), leaking all users' analyses.
- **Committed weak default passwords** — `SecureAI2024!DB` and `change-this-in-production` appear as real fallbacks in `docker-compose.quick.yml` / `.https.yml` / `.prod.yml`; quick-deploy Redis runs with no password.
- **`.dockerignore` could not be verified** in this environment — must confirm it excludes `.env*`, `secrets/`, `wallet/`, `certs/`, `*.pem`, `*.key`, because `Dockerfile:54` does `COPY . .` and `deploy.yml` pushes images to ghcr.io on every push.
- **Solana private key only base64-encoded, not encrypted** (`api.py:556-559`).
- **Docker healthcheck path mismatch** — curls `/api/health`, but the FastAPI app exposes `/health`.
- **`secureai.service` is broken** — references a non-existent `gunicorn.conf.py` (actual: `gunicorn_config.py`) and lacks the hardening the guardian unit has.
- **Doc/route schism** — AGENTS.md says run Flask `api.py` (`/api/analyze`), but the frontend calls FastAPI `/api/v1/*`; following the docs verbatim 404s every scan. `conftest.py` points tests at the stale Flask endpoint too.
- **`>=` dependency pinning + no Python lockfile** — non-reproducible builds; torch installed fully unpinned.
- **Error paths report failure as "real"** — `detect.py:127-135` returns `is_fake: False, score: 0.5` on hard failure; nearly every detector returns `0.5` on exception, masking breakage behind a confident-looking verdict.

---

## Low-severity / cleanliness

`print()` instead of logging (~28 sites); duplicated `_make_json_serializable` and triplicated Redis clients; dead code (`performance/caching.py`, `require_login`, `main.py`, `aistore_integration.py`, `jetson_inference.py`); ~50 production `console.log`s (incl. logging all response headers, `apiService.ts:585`); TypeScript not in `strict` mode; oversized React components (Dashboard/Scanner/Results 24–34KB); ~30 stray debug `.md` files + `.bat` scripts in the frontend root; `index.html` dual-loads React from esm.sh CDN *and* the bundle (dual-instance risk); broken format strings `print(".2f")` in several files.

---

## Test suite reality check

There are ~50 test functions, but **only `tests/test_api_endpoints.py` actually runs and asserts anything** in CI (15 server-free FastAPI contract checks — genuinely good). The accuracy/adversarial/bias suites compute real metrics but **skip on empty `tests/test_data/`** and point at the stale Flask endpoint, so they assert nothing. `test_navigation_context.py` imports a non-existent `src/` package and fails at collection. `test_performance.py` passes vacuously when the server is down. **No test verifies that detection is real** — a regression making the model output constant/garbage would not be caught. Combined with H9 (CI can't fail), the test suite provides little real safety today.

---

## Recommended next steps (prioritized)

### Phase 0 — Stop the bleeding (this week)
1. **Rotate** the AWS keys (C3) and X session cookies; move all secret material out of the repo tree. Verify no secret-bearing image was already pushed to ghcr.io.
2. **Require a real `JWT_SECRET_KEY`** at startup; fail closed if unset (C4).
3. **Verify/fix `.dockerignore`** to exclude `.env*`, `secrets/`, `wallet/`, `certs/`, `*.pem`, `*.key`.
4. **Add auth + size limits + an SSRF allowlist** to the detect endpoints (C5, H1, H2).

### Phase 1 — Make detection honest (next 2–4 weeks)
5. **Switch the production path to the real models** — route the API to `EnhancedDetector` (or a cleaned successor) that loads `trained_models/resnet50_celeb_df_v2.pth` + ConvNeXt + the learned ensemble weights. **Delete** the leakage `resnet_resnet50_*.pth` and the untrained Xception/EfficientNet/CLIP/LAA from the live ensemble (or fix them properly — LAA needs aligned face crops; CLIP needs a trained head).
6. **Apply face detection** before inference (H5).
7. **Re-state benchmarks truthfully** in the README from the actual result files (ResNet50 0.906, ensemble 0.927); remove the 94.2%/0.967 claims and the "diffusion/Morpheus" marketing until they exist (C1, C2).
8. **Replace `np.random` security scoring** with a real signal or remove the feature.

### Phase 2 — Consolidate the backend (next 1–2 months)
9. **Pick one server** (FastAPI `app/`). Delete `api.py`, `main.py`, `performance/caching.py`; reconcile AGENTS.md, gunicorn config, nginx, and tests to the chosen app.
10. **Fix `get_db()` consumption** (use proper `Depends(get_db)` / context manager) — C6.
11. **Repair the Celery pipeline** so heavy inference is async (H4); move per-request state to Redis/DB (multi-worker correctness).
12. **Make CI able to fail** — hard-fail Gitleaks/TruffleHog/pip-audit and the API tests on `master`/`main` (H9).

### Phase 3 — Hardening & quality
13. Lock CORS to known origins; add proxy rate limiting + per-route body limits (H6, H10); remove committed default passwords.
14. Add a **real detection-correctness test** (known-fake / known-real fixtures asserting verdicts) so the ML can't silently regress.
15. Backend-validate subscription tier (H7); remove/clean the legacy Flask UI (H8); pin Python deps with a lockfile.

---

## Suggested decision points for our discussion

- **Positioning:** is this a research/portfolio project, a product you intend to sell, or something you're raising on? That changes how urgent the "honest benchmarks" issue is — if anyone external sees the 94.2% number, fixing it is Phase 0, not Phase 1.
- **Backend direction:** commit to FastAPI and delete Flask, or the reverse? Half-and-half is currently costing you the most.
- **Model strategy:** ship the honest 0.91-AUC ResNet now and iterate, or invest in genuinely integrating LAA-Net/CLIP (face alignment + trained heads) before relaunching detection?
- **Scope:** which of blockchain, Celery training, Jetson, Morpheus, AIStore are real roadmap vs. things to cut? A lot of surface area is currently non-functional.
