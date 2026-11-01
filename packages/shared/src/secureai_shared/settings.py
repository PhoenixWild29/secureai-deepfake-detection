"""Runtime settings. Secrets come from the environment, never from the repo."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from secureai_shared.attestation import AttestationKeyError, load_attestation_key, normalize_pem, validate_key_id


def _csv(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


@dataclass(frozen=True)
class Settings:
    auth_mode: str
    clerk_issuer: str
    clerk_jwks_url: str
    clerk_authorized_parties: tuple[str, ...]
    database_url: str
    redis_url: str
    queue_backend: str
    queue_key: str
    storage_backend: str
    media_root: str
    s3_endpoint: str
    s3_bucket: str
    s3_access_key_id: str
    s3_secret_access_key: str
    s3_region: str
    cors_origins: tuple[str, ...]
    dev_subject: str
    max_upload_bytes: int
    detector_timeout_seconds: float = 60.0
    stuck_job_seconds: float = 180.0
    job_max_attempts: int = 3
    rate_limit_jobs: int = 30
    rate_limit_uploads: int = 60
    rate_limit_window_seconds: int = 60
    s3_auto_create_bucket: bool = False
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_pro: str = ""
    stripe_price_team: str = ""
    public_app_url: str = "http://localhost:3000"
    quota_mode: str = "enforce"
    quota_free: int = 10
    quota_pro: int = 500
    quota_team: int = 2000
    seat_limit_free: int = 3
    seat_limit_team: int = 25
    webhook_max_attempts: int = 5
    webhook_timeout_seconds: float = 10.0
    attestation_private_key: str = ""
    attestation_key_id: str = "v1"
    rate_limit_attestations: int = 60
    rate_limit_api_keys: int = 10
    sentry_dsn: str = ""
    sentry_environment: str = ""
    admin_user_ids: tuple[str, ...] = ()


def assert_explicit_origins(origins: tuple[str, ...]) -> None:
    """Reject wildcard CORS. Job routes send Authorization, so * is not safe."""

    if "*" in origins:
        raise RuntimeError(
            "CORS_ORIGINS=* is not allowed. List explicit origins, for example "
            "http://localhost:3000. Do not use a wildcard on a deployed API."
        )


def load_settings(
    environ: Mapping[str, str] | None = None,
    *,
    role: str = "api",
) -> Settings:
    """Load settings.

    The API defaults to Clerk and refuses to boot without CLERK_ISSUER.
    AUTH_MODE=dev is a workstation bypass. The worker does not check JWTs,
    so it does not require CLERK_ISSUER.
    """

    env = os.environ if environ is None else environ
    if role not in {"api", "worker"}:
        raise RuntimeError(f"Unknown settings role {role!r}")

    auth_mode = env.get("AUTH_MODE", "clerk").strip().lower() or "clerk"
    if auth_mode not in {"clerk", "dev"}:
        raise RuntimeError("AUTH_MODE must be 'clerk' or 'dev'")

    issuer = env.get("CLERK_ISSUER", "").strip().rstrip("/")
    if role == "api" and auth_mode == "clerk" and not issuer:
        raise RuntimeError(
            "Job routes require a verified Clerk JWT. Set CLERK_ISSUER to the "
            "Clerk Frontend API origin (https://<slug>.clerk.accounts.dev) or "
            "set AUTH_MODE=dev only on a private workstation. Do not expose "
            "AUTH_MODE=dev on a public host."
        )

    origins = _csv(env.get("CORS_ORIGINS", "http://localhost:3000"))
    if not origins:
        origins = ("http://localhost:3000",)
    assert_explicit_origins(origins)

    queue_backend = env.get("QUEUE_BACKEND", "redis").strip().lower() or "redis"
    if queue_backend not in {"redis", "memory"}:
        raise RuntimeError("QUEUE_BACKEND must be 'redis' or 'memory'")
    redis_url = env.get("REDIS_URL", "").strip()
    if queue_backend == "redis" and not redis_url:
        raise RuntimeError("QUEUE_BACKEND=redis requires REDIS_URL")

    database_url = env.get("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    storage_backend = env.get("STORAGE_BACKEND", "filesystem").strip().lower() or "filesystem"
    if storage_backend not in {"filesystem", "s3"}:
        raise RuntimeError("STORAGE_BACKEND must be 'filesystem' or 's3'")

    s3_bucket = env.get("S3_BUCKET", "").strip()
    s3_key = env.get("S3_ACCESS_KEY_ID", "").strip()
    s3_secret = env.get("S3_SECRET_ACCESS_KEY", "").strip()
    if storage_backend == "s3" and not (s3_bucket and s3_key and s3_secret):
        raise RuntimeError(
            "STORAGE_BACKEND=s3 requires S3_BUCKET, S3_ACCESS_KEY_ID, and S3_SECRET_ACCESS_KEY"
        )

    detector_timeout = _positive_float(env, "DETECTOR_TIMEOUT_SECONDS", 60.0)
    stuck_after = _positive_float(env, "STUCK_JOB_SECONDS", 180.0)
    if stuck_after <= detector_timeout:
        raise RuntimeError(
            "STUCK_JOB_SECONDS must be greater than DETECTOR_TIMEOUT_SECONDS "
            "so a live detection is not swept as abandoned"
        )
    max_attempts = _positive_int(env, "JOB_MAX_ATTEMPTS", 3)
    rate_jobs = _nonnegative_int(env, "RATE_LIMIT_JOBS", 30)
    rate_uploads = _nonnegative_int(env, "RATE_LIMIT_UPLOADS", 60)
    rate_window = _positive_int(env, "RATE_LIMIT_WINDOW_SECONDS", 60)
    auto_create = env.get("S3_AUTO_CREATE_BUCKET", "false").strip().lower() in {
        "1",
        "true",
        "yes",
    }

    try:
        attestation_pem = normalize_pem(env.get("ATTESTATION_PRIVATE_KEY", ""))
        attestation_key_id = validate_key_id(env.get("ATTESTATION_KEY_ID", ""))
        if attestation_pem:
            load_attestation_key(attestation_pem, attestation_key_id)
    except AttestationKeyError as exc:
        raise RuntimeError(str(exc)) from exc

    stripe_secret = env.get("STRIPE_SECRET_KEY", "").strip()
    public_app = env.get("PUBLIC_APP_URL", "http://localhost:3000").strip().rstrip("/")
    public_app = public_app or "http://localhost:3000"
    if not public_app.startswith(("http://", "https://")):
        raise RuntimeError("PUBLIC_APP_URL must be an http(s) origin")

    return Settings(
        auth_mode=auth_mode,
        clerk_issuer=issuer,
        clerk_jwks_url=env.get("CLERK_JWKS_URL", "").strip(),
        clerk_authorized_parties=_csv(env.get("CLERK_AUTHORIZED_PARTIES", "")),
        database_url=database_url,
        redis_url=redis_url,
        queue_backend=queue_backend,
        queue_key=env.get("QUEUE_KEY", "secureai:jobs").strip() or "secureai:jobs",
        storage_backend=storage_backend,
        media_root=env.get("MEDIA_ROOT", ".media").strip() or ".media",
        s3_endpoint=env.get("S3_ENDPOINT", "").strip(),
        s3_bucket=s3_bucket,
        s3_access_key_id=s3_key,
        s3_secret_access_key=s3_secret,
        s3_region=env.get("S3_REGION", "us-east-1").strip() or "us-east-1",
        cors_origins=origins,
        dev_subject=env.get("DEV_AUTH_SUBJECT", "user_dev").strip() or "user_dev",
        max_upload_bytes=50_000_000,
        detector_timeout_seconds=detector_timeout,
        stuck_job_seconds=stuck_after,
        job_max_attempts=max_attempts,
        rate_limit_jobs=rate_jobs,
        rate_limit_uploads=rate_uploads,
        rate_limit_window_seconds=rate_window,
        s3_auto_create_bucket=auto_create,
        stripe_secret_key=stripe_secret,
        stripe_webhook_secret=env.get("STRIPE_WEBHOOK_SECRET", "").strip(),
        stripe_price_pro=env.get("STRIPE_PRICE_PRO", "").strip(),
        stripe_price_team=env.get("STRIPE_PRICE_TEAM", "").strip(),
        public_app_url=public_app,
        quota_mode=_quota_mode(env, auth_mode, stripe_secret),
        quota_free=_positive_int(env, "QUOTA_FREE", 10),
        quota_pro=_positive_int(env, "QUOTA_PRO", 500),
        quota_team=_positive_int(env, "QUOTA_TEAM", 2000),
        seat_limit_free=_positive_int(env, "SEAT_LIMIT_FREE", 3),
        seat_limit_team=_positive_int(env, "SEAT_LIMIT_TEAM", 25),
        webhook_max_attempts=_bounded_int(env, "WEBHOOK_MAX_ATTEMPTS", 5, upper=10),
        webhook_timeout_seconds=_bounded_float(env, "WEBHOOK_TIMEOUT_SECONDS", 10.0, upper=30.0),
        attestation_private_key=attestation_pem,
        attestation_key_id=attestation_key_id,
        rate_limit_attestations=_nonnegative_int(env, "RATE_LIMIT_ATTESTATIONS", 60),
        rate_limit_api_keys=_nonnegative_int(env, "RATE_LIMIT_API_KEYS", 10),
        sentry_dsn=env.get("SENTRY_DSN", "").strip(),
        sentry_environment=env.get("SENTRY_ENVIRONMENT", "").strip(),
        admin_user_ids=_csv(env.get("ADMIN_USER_IDS", "")),
    )


def _quota_mode(env: Mapping[str, str], auth_mode: str, stripe_secret: str) -> str:
    """Dev without Stripe does not enforce quotas. Production stays on the free trial."""

    explicit = env.get("QUOTA_MODE", "").strip().lower()
    if explicit:
        if explicit not in {"enforce", "unlimited"}:
            raise RuntimeError("QUOTA_MODE must be 'enforce' or 'unlimited'")
        return explicit
    if not stripe_secret and auth_mode == "dev":
        return "unlimited"
    return "enforce"


def _positive_float(env: Mapping[str, str], name: str, default: float) -> float:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a number") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than 0")
    return value


def _positive_int(env: Mapping[str, str], name: str, default: int) -> int:
    value = int(_positive_float(env, name, float(default)))
    if value < 1:
        raise RuntimeError(f"{name} must be at least 1")
    return value


def _bounded_int(env: Mapping[str, str], name: str, default: int, *, upper: int) -> int:
    value = _positive_int(env, name, default)
    if value > upper:
        raise RuntimeError(f"{name} must be at most {upper}")
    return value


def _bounded_float(env: Mapping[str, str], name: str, default: float, *, upper: float) -> float:
    value = _positive_float(env, name, default)
    if value > upper:
        raise RuntimeError(f"{name} must be at most {upper}")
    return value


def _nonnegative_int(env: Mapping[str, str], name: str, default: int) -> int:
    raw = env.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < 0:
        raise RuntimeError(f"{name} must be 0 or greater")
    return value
