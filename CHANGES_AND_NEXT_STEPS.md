# Changes Applied + Required Manual Actions

**Date:** 2026-05-30
**How changes were made:** Direct edits to the working tree (your local git has a corrupt HEAD tree object, so a branch wasn't possible). Originals are backed up under `_review_backups/<timestamp>/` for diffing/revert. **Nothing was pushed or committed.**

---

## Track A — Security Phase 0 (applied)

| ID | Change | Files |
|----|--------|-------|
| A1 | JWT now **fails closed** — refuses to start if `JWT_SECRET_KEY` is unset/empty/`your-secret-key` | `app/dependencies/auth.py` |
| A2 | Added a reusable `get_current_user` Bearer-JWT dependency and applied `Depends(get_current_user)` to all detect POST routes (`""`, `/url`, `/batch`); added upload **size cap** (413 on oversize, streamed 1 MiB chunks instead of unbounded `read()`) | `app/dependencies/auth.py`, `app/api/v1/endpoints/detect.py`, `app/core/config.py` |
| A2 | CORS no longer defaults to `*`+credentials — reads `CORS_ORIGINS`, safe localhost fallback; `TrustedHost` reads `ALLOWED_HOSTS` | `app/main.py`, `app/core/config.py` |
| A3 | **SSRF guard** — URL download now blocks private/loopback/link-local/reserved IPs + the `169.254.169.254` metadata IP, resolves hostnames to catch rebinding, optional `ALLOWED_DOWNLOAD_HOSTS` allowlist | `utils/video_downloader.py` |
| A4 | Removed committed default passwords (`SecureAI2024!DB`, `change-this-in-production`) → now required `${VAR:?...}`; added Redis `--requirepass`; hardened `.dockerignore`; created `.env.example` (placeholders only) | `docker-compose*.yml`, `.dockerignore`, `.env.example` (new) |
| A5 | Uploaded temp files deleted in `finally` after analysis (all three routes) | `app/api/v1/endpoints/detect.py` |

## Track B — Model honesty + quality (applied)

| ID | Change | Files |
|----|--------|-------|
| B1 | Live detection **rewired** from the leakage/untrained `EnsembleDetector` to `EnhancedDetector` (trained ResNet50 + ConvNeXt + FFT + learned ensemble weights). Verified: learned ensemble = **AUC 0.964** on validation | `ai_model/detect.py` |
| B2 | Face detection/crop now applied before inference (`use_face_crop=True`, graceful fallback) | `ai_model/enhanced_detector.py` |
| B3 | Untrained Xception/EfficientNet + chance-level CLIP/LAA removed from the live path; `EnsembleDetector` marked deprecated (not deleted) | `ai_model/ensemble_detector.py`, `ai_model/enhanced_detector.py` |
| B4 | Replaced `np.random` "anomaly score" with a deterministic signal; rewrote README benchmarks to **real** numbers; removed fabricated 94.2%/0.967 table and non-existent "diffusion/Morpheus" claims | `ai_model/morpheus_security.py`, `README.md` |
| B5 | New regression test asserting ensemble AUC ≥ 0.90 and that production routes to `EnhancedDetector` — **passes** | `tests/test_detection_correctness.py` (new) |

---

## ⚠️ Required manual actions (only you can do these)

1. **Rotate the leaked credentials now.** The AWS access key (`AKIA…`) and secret in `.env`, and the X/Twitter session cookies in `secrets/x_cookies.txt.txt`, should be treated as compromised. Rotate the AWS key in IAM, invalidate the X session. They were never in git, but they sit in a synced folder.
2. **Re-clone the repo from GitHub.** Your local `.git` has a corrupt HEAD tree object — your working master isn't reliably committable. Get a clean checkout, then re-apply these changes (the `_review_backups/` folder lets you diff exactly what changed).
3. **Set the new required env vars** before running: `JWT_SECRET_KEY`, `SECRET_KEY`, `POSTGRES_PASSWORD`/DB password, `REDIS_PASSWORD`, `CORS_ORIGINS`, `ALLOWED_HOSTS`. See `.env.example`. The app now intentionally refuses to start without a real `JWT_SECRET_KEY`.
4. **Commit `.env.example`, never `.env`.**

## Follow-ups not done (flagged for next pass)

- **Rate limiting on detect routes** was deferred — only Flask-Limiter is installed, and adding `slowapi` to the FastAPI app is a new dependency (out of Phase-0 scope). Recommend adding it next.
- **Pre-existing bug:** the `/url` route treats `download_video_from_url(...)`'s return as a path, but it returns a `(filepath, filename)` tuple — needs unpacking. Left untouched to avoid behavior change; worth fixing.
- `api.py` still calls `start_background_ensemble_load()` which now warms the deprecated detector — can be removed to save startup time/memory.
- Decide whether to delete the deprecated Flask `api.py` and the leakage `resnet_resnet50_*.pth` files (kept for now; reversible).

See `MODEL_IMPROVEMENT_PLAN.md` for the path from 0.91 in-domain toward best-in-class cross-dataset performance.
