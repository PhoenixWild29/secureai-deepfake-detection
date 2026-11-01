"""The SDK init used by the API actually scrubs an event before send."""

from __future__ import annotations

import json

from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

from conftest import make_settings
from secureai_shared.reporting import error_reporting_enabled, init_error_reporting


class _MemoryTransport(Transport):
    def __init__(self, options: object = None) -> None:
        super().__init__(options)  # type: ignore[arg-type]
        self.events: list[dict[str, object]] = []

    def capture_envelope(self, envelope: Envelope) -> None:
        for item in envelope.items:
            if item.headers.get("type") != "event":
                continue
            payload = item.payload.json
            if isinstance(payload, dict):
                self.events.append(payload)


def test_sdk_scrubs_secrets_before_the_transport(tmp_path) -> None:
    transport = _MemoryTransport()
    settings = make_settings(
        tmp_path,
        auth_mode="clerk",
        sentry_dsn="https://public@o0.ingest.sentry.io/1",
        sentry_environment="test",
    )
    try:
        assert init_error_reporting(settings, service="secureai-api", transport=transport) is True
        assert error_reporting_enabled() is True
        import sentry_sdk

        scope = sentry_sdk.get_current_scope()
        scope.set_extra("stripe_secret", "whsec_live")
        scope.set_extra("filename", "clip.mp4")
        try:
            raise RuntimeError("Bearer super-secret-token postgresql://app:dbpassword@db.internal/app")
        except RuntimeError as exc:
            sentry_sdk.capture_exception(exc)
        sentry_sdk.flush(timeout=5)
        assert transport.events
        blob = json.dumps(transport.events[-1])
        assert "super-secret-token" not in blob
        assert "dbpassword" not in blob
        assert "whsec_live" not in blob
        assert "clip.mp4" in blob
        assert "public@" not in blob
    finally:
        init_error_reporting(make_settings(tmp_path), service="secureai-api")
        assert error_reporting_enabled() is False
