import pytest

from secureai_shared.settings import load_settings


def test_api_clerk_mode_requires_issuer() -> None:
    with pytest.raises(RuntimeError, match="CLERK_ISSUER"):
        load_settings({"DATABASE_URL": "postgresql+psycopg://db", "REDIS_URL": "redis://localhost:6379/0"}, role="api")


def test_worker_clerk_mode_does_not_require_issuer() -> None:
    settings = load_settings(
        {"DATABASE_URL": "postgresql+psycopg://db", "REDIS_URL": "redis://localhost:6379/0"},
        role="worker",
    )
    assert settings.auth_mode == "clerk"
    assert settings.queue_backend == "redis"
    assert settings.cors_origins == ("http://localhost:3000",)


def test_cors_wildcard_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        load_settings(
            {
                "AUTH_MODE": "dev",
                "DATABASE_URL": "postgresql+psycopg://db",
                "REDIS_URL": "redis://localhost:6379/0",
                "CORS_ORIGINS": "*",
            },
            role="api",
        )


def test_dev_mode_still_requires_database_and_redis() -> None:
    settings = load_settings(
        {
            "AUTH_MODE": "dev",
            "DATABASE_URL": "postgresql+psycopg://db",
            "REDIS_URL": "redis://localhost:6379/0",
        },
        role="api",
    )
    assert settings.auth_mode == "dev"
    assert settings.dev_subject == "user_dev"


def test_s3_bucket_auto_create_stays_off() -> None:
    settings = load_settings(
        {
            "AUTH_MODE": "dev",
            "DATABASE_URL": "postgresql+psycopg://db",
            "REDIS_URL": "redis://localhost:6379/0",
            "STORAGE_BACKEND": "s3",
            "S3_BUCKET": "secureai",
            "S3_ACCESS_KEY_ID": "key",
            "S3_SECRET_ACCESS_KEY": "secret",
        },
        role="api",
    )
    assert settings.s3_auto_create_bucket is False
    enabled = load_settings(
        {
            "AUTH_MODE": "dev",
            "DATABASE_URL": "postgresql+psycopg://db",
            "REDIS_URL": "redis://localhost:6379/0",
            "STORAGE_BACKEND": "s3",
            "S3_BUCKET": "secureai",
            "S3_ACCESS_KEY_ID": "key",
            "S3_SECRET_ACCESS_KEY": "secret",
            "S3_AUTO_CREATE_BUCKET": "true",
        },
        role="worker",
    )
    assert enabled.s3_auto_create_bucket is True


def test_stuck_lease_must_outlast_the_detector() -> None:
    with pytest.raises(RuntimeError, match="STUCK_JOB_SECONDS"):
        load_settings(
            {
                "AUTH_MODE": "dev",
                "DATABASE_URL": "postgresql+psycopg://db",
                "REDIS_URL": "redis://localhost:6379/0",
                "DETECTOR_TIMEOUT_SECONDS": "60",
                "STUCK_JOB_SECONDS": "60",
            },
            role="worker",
        )


def test_redis_backend_requires_url() -> None:
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        load_settings({"AUTH_MODE": "dev", "DATABASE_URL": "postgresql+psycopg://db"}, role="worker")
