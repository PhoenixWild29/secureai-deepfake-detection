"""Sentry stays off without a DSN, and events do not carry secrets."""

from __future__ import annotations

from typing import Any

from secureai_shared.reporting import (
    error_reporting_enabled,
    init_error_reporting,
    redact_text,
    scrub_event,
)
from secureai_shared.settings import Settings


class _FakeSDK:
    def __init__(self) -> None:
        self.kwargs: dict[str, Any] | None = None
        self.tags: list[tuple[str, str]] = []

    def init(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def set_tag(self, key: str, value: str) -> None:
        self.tags.append((key, value))


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "auth_mode": "dev",
        "clerk_issuer": "",
        "clerk_jwks_url": "",
        "clerk_authorized_parties": (),
        "database_url": "postgresql+psycopg://unused/unused",
        "redis_url": "",
        "queue_backend": "memory",
        "queue_key": "secureai:jobs",
        "storage_backend": "filesystem",
        "media_root": ".media",
        "s3_endpoint": "",
        "s3_bucket": "",
        "s3_access_key_id": "",
        "s3_secret_access_key": "",
        "s3_region": "us-east-1",
        "cors_origins": ("http://localhost:3000",),
        "dev_subject": "user_dev",
        "max_upload_bytes": 50_000_000,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_sentry_disabled_without_dsn() -> None:
    sdk = _FakeSDK()
    settings = _settings()
    assert settings.sentry_dsn == ""
    assert init_error_reporting(settings, service="secureai-api", sdk=sdk) is False
    assert sdk.kwargs is None
    assert error_reporting_enabled() is False


def test_dev_dsn_is_labeled_development_and_drops_bodies() -> None:
    sdk = _FakeSDK()
    settings = _settings(sentry_dsn="https://public@o0.ingest.sentry.io/1")
    assert init_error_reporting(settings, service="secureai-worker", sdk=sdk) is True
    assert sdk.kwargs is not None
    assert sdk.kwargs["dsn"] == settings.sentry_dsn
    assert sdk.kwargs["environment"] == "development"
    assert sdk.kwargs["include_local_variables"] is False
    assert sdk.kwargs["include_source_context"] is False
    assert sdk.kwargs["data_collection"]["frame_context_lines"] == 0
    assert sdk.kwargs["max_request_body_size"] == "never"
    assert sdk.kwargs["traces_sample_rate"] is None
    assert sdk.kwargs["default_integrations"] is False
    assert sdk.kwargs["data_collection"]["http_bodies"] == []
    assert sdk.kwargs["data_collection"]["user_info"] is False
    assert sdk.kwargs["data_collection"]["stack_frame_variables"] is False
    assert sdk.kwargs["data_collection"]["http_headers"]["request"]["mode"] == "off"
    assert sdk.kwargs["before_send"] is scrub_event
    assert "send_default_pii" not in sdk.kwargs
    names = [type(item).__name__ for item in sdk.kwargs["integrations"]]
    assert names == ["LoggingIntegration", "DedupeIntegration"]
    assert sdk.tags == [("service", "secureai-worker")]
    assert error_reporting_enabled() is True
    # Leave the process quiet for later tests. The fake client never sent.
    assert init_error_reporting(_settings(), service="secureai-worker", sdk=sdk) is False
    assert error_reporting_enabled() is False


def test_api_integrations_include_the_framework_hooks() -> None:
    sdk = _FakeSDK()
    settings = _settings(
        auth_mode="clerk",
        sentry_dsn="https://public@o0.ingest.sentry.io/1",
        sentry_environment="staging",
    )
    assert init_error_reporting(settings, service="secureai-api", sdk=sdk) is True
    assert sdk.kwargs is not None
    assert sdk.kwargs["environment"] == "staging"
    names = [type(item).__name__ for item in sdk.kwargs["integrations"]]
    assert names == [
        "StarletteIntegration",
        "FastApiIntegration",
        "LoggingIntegration",
        "DedupeIntegration",
    ]
    logging_integration = sdk.kwargs["integrations"][2]
    assert logging_integration._handler is None
    init_error_reporting(_settings(), service="secureai-api", sdk=sdk)


def test_scrub_event_drops_auth_bodies_and_secrets() -> None:
    event = {
        "message": "Bearer super-secret-token failed",
        "request": {
            "url": "https://api.example/v1/jobs?token=abc",
            "query_string": "token=abc",
            "headers": {
                "Authorization": "Bearer super-secret-token",
                "Cookie": "session=1",
                "Content-Type": "application/json",
                "X-Org-Id": "org_123",
            },
            "cookies": {"session": "1"},
            "data": b"video-bytes",
            "env": {"HTTP_AUTHORIZATION": "Bearer super-secret-token"},
        },
        "user": {"id": "user_1", "email": "person@example.com", "ip_address": "203.0.113.4"},
        "extra": {
            "stripe_secret": "whsec_live",
            "filename": "clip.mp4",
            "media": b"\x00\x01",
            "note": "postgres postgresql://app:dbpassword@db.internal/app",
        },
        "exception": {
            "values": [
                {
                    "type": "RuntimeError",
                    "value": "connect postgresql://app:dbpassword@db.internal/app",
                    "stacktrace": {"frames": [{"filename": "app.py", "vars": {"token": "super-secret-token"}}]},
                }
            ]
        },
    }
    scrubbed = scrub_event(event, {})
    request = scrubbed["request"]
    assert request["headers"] == {"Content-Type": "application/json"}
    assert "cookies" not in request
    assert "data" not in request
    assert "env" not in request
    assert request["query_string"] == ""
    assert request["url"] == "https://api.example/v1/jobs"
    assert scrubbed["user"] == {"id": "user_1"}
    assert scrubbed["extra"]["stripe_secret"] == "[Filtered]"
    assert scrubbed["extra"]["filename"] == "clip.mp4"
    assert scrubbed["extra"]["media"] == "[Filtered]"
    assert "dbpassword" not in scrubbed["extra"]["note"]
    assert "super-secret-token" not in scrubbed["message"]
    frame = scrubbed["exception"]["values"][0]
    assert "dbpassword" not in frame["value"]
    assert "vars" not in frame["stacktrace"]["frames"][0]
    blob = str(scrubbed)
    assert "super-secret-token" not in blob
    assert "dbpassword" not in blob
    assert "whsec_live" not in blob
    assert "person@example.com" not in blob


def test_redact_text_covers_sentry_dsn_userinfo() -> None:
    raw = "dsn https://abc123def@o0.ingest.sentry.io/1 and Bearer eyJhbGciOi"
    cleaned = redact_text(raw)
    assert "abc123def" not in cleaned
    assert "eyJhbGciOi" not in cleaned
    assert "[Filtered]" in cleaned


def test_redact_text_hides_api_key_secrets_and_keeps_prefixes() -> None:
    secret = "sai_" + "a" * 40
    cleaned = redact_text(f"created {secret} prefix sai_abcd1234")
    assert secret not in cleaned
    assert "sai_abcd1234" in cleaned
    assert "sai_[Filtered]" in cleaned
    bearer = redact_text("Authorization Bearer " + secret)
    assert secret not in bearer
