"""Optional Sentry reporting for the API and worker.

An empty ``SENTRY_DSN`` does not import the SDK and does not send events.
The DSN itself is never logged.
"""

from __future__ import annotations

import copy
import logging
import re
from typing import Any

from secureai_shared.settings import Settings

logger = logging.getLogger("secureai.reporting")

_SERVICE_API = "secureai-api"
_SERVICE_WORKER = "secureai-worker"

# Userinfo in a URL is a secret (database passwords, Redis passwords, Sentry DSNs).
_URL_USERINFO = re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://)([^/\s@]+)@")
_BEARER = re.compile(r"(?i)\bBearer\s+\S+")
# Full secrets are sai_ plus at least 16 token characters. A 12-character prefix stays visible.
_API_KEY = re.compile(r"\bsai_[A-Za-z0-9_-]{16,}\b")
# A URL whose query carries a signature or an AWS credential is a presigned
# URL. Keep the object URL and drop the whole query string.
_PRESIGNED_QUERY = re.compile(
    r"(?i)(https?://[^\s?\"'<>]+)\?[^\s\"'<>]*"
    r"(?:x-amz-signature|x-amz-credential|x-amz-security-token|awsaccesskeyid|signature)="
    r"[^\s\"'<>]*"
)
# Other sensitive query values. The parameter name stays, matching the sai_
# style of keeping a short non-secret prefix and filtering the secret.
# A leading ``?`` or ``&`` is not consumed, so ``?token=secret`` stays readable
# as ``?token=[Filtered]``.
_SENSITIVE_QUERY = re.compile(
    r"(?im)((?:^|(?<=[?&\s]))"
    r"(?:"
    r"[a-z0-9_.-]*"
    r"(?:password|passwd|secret|token|signature|credential|session|authorization|dsn|"
    r"access[-_]?key|api[-_]?key)"
    r"[a-z0-9_.-]*)=)"
    r"([^&#\s\"']*)"
)
_SQL_PARAMETERS = "[parameters:"
_SECRET_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "authorization",
    "cookie",
    "credential",
    "private_key",
    "access_key",
    "api_key",
    "apikey",
    "dsn",
    "session",
    "signature",
)
_HEADER_ALLOW = frozenset({"accept", "content-length", "content-type", "user-agent"})
_FILTERED = "[Filtered]"

# Explicit opt-out. Omitted data_collection fields default to collecting data,
# and setting data_collection disables the SDK's EventScrubber, so before_send
# is the scrubber.
_DATA_COLLECTION: dict[str, Any] = {
    "user_info": False,
    "cookies": {"mode": "off"},
    "http_headers": {"request": {"mode": "off"}},
    "http_bodies": [],
    "url_query_params": {"mode": "off"},
    "gen_ai": {"inputs": False, "outputs": False},
    "database_query_data": False,
    "queues": False,
    "stack_frame_variables": False,
    "frame_context_lines": 0,
    "graphql": {"document": False, "variables": False},
}


class _State:
    enabled: bool = False
    started: bool = False


_state = _State()


def error_reporting_enabled() -> bool:
    return _state.enabled


def init_error_reporting(
    settings: Settings,
    *,
    service: str,
    sdk: Any | None = None,
    transport: Any | None = None,
) -> bool:
    """Turn reporting on when ``settings.sentry_dsn`` is set.

    Returns False without importing ``sentry_sdk`` when the DSN is empty,
    unless a previous call in this process already started the SDK. That
    later call disables the client so a test or a reload cannot keep sending.
    """

    dsn = settings.sentry_dsn.strip()
    if not dsn:
        _state.enabled = False
        if _state.started:
            _disable_started_client()
        return False

    if sdk is None:
        try:
            import sentry_sdk as imported
        except ImportError as exc:
            raise RuntimeError("SENTRY_DSN is set but sentry-sdk is not installed") from exc
        sdk = imported

    options: dict[str, Any] = {
        "dsn": dsn,
        "environment": _environment(settings),
        "server_name": service,
        "traces_sample_rate": None,
        "include_local_variables": False,
        "include_source_context": False,
        "max_request_body_size": "never",
        "auto_session_tracking": False,
        "data_collection": copy.deepcopy(_DATA_COLLECTION),
        "before_send": scrub_event,
        "default_integrations": False,
        "integrations": _integrations(service),
        "in_app_include": ["app", "worker", "secureai_shared", "detector"],
    }
    if transport is not None:
        options["transport"] = transport
    sdk.init(**options)
    set_tag = getattr(sdk, "set_tag", None)
    if callable(set_tag):
        set_tag("service", service)
    _state.started = True
    _state.enabled = True
    logger.info("error reporting enabled service=%s", service)
    return True


def capture_exception(exc: BaseException) -> None:
    """Send ``exc`` when reporting is on. A missing DSN drops it."""

    if not _state.enabled:
        return
    import sentry_sdk

    sentry_sdk.capture_exception(exc)


def scrub_event(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
    """Drop auth material, request bodies, and credential URLs before send.

    LoggingIntegration builds the event in ``callHandlers``, after logger
    filters and before handler filters. A log-derived event therefore depends
    on this function: ``message``, ``logentry`` (including tuple ``params``),
    and exception values all go through ``redact_text``.
    """

    del hint
    request = event.get("request")
    if isinstance(request, dict):
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = {
                key: value
                for key, value in headers.items()
                if isinstance(key, str) and key.lower() in _HEADER_ALLOW
            }
        elif isinstance(headers, list):
            request["headers"] = [
                pair
                for pair in headers
                if isinstance(pair, (list, tuple))
                and len(pair) == 2
                and isinstance(pair[0], str)
                and pair[0].lower() in _HEADER_ALLOW
            ]
        request.pop("cookies", None)
        request.pop("data", None)
        request.pop("env", None)
        query = request.get("query_string")
        if isinstance(query, str):
            request["query_string"] = ""
        url = request.get("url")
        if isinstance(url, str) and "?" in url:
            request["url"] = url.split("?", 1)[0]
        event["request"] = request

    user = event.get("user")
    if isinstance(user, dict):
        kept = user.get("id")
        event["user"] = {"id": kept} if isinstance(kept, str) and kept else {}

    _drop_frame_vars(event)
    _scrub_tree(event)
    return event


def redact_text(value: str) -> str:
    """Remove secrets from a log line or a Sentry string.

    A full ``sai_`` secret becomes ``sai_[Filtered]``. A shorter prefix, such
    as the 12-character value stored on the key row, stays visible. Query
    parameters keep their names and lose their values. A presigned S3 URL
    keeps the scheme, host, and path only.
    """

    value = _URL_USERINFO.sub(r"\1" + _FILTERED + "@", value)
    value = _BEARER.sub("Bearer " + _FILTERED, value)
    value = _API_KEY.sub("sai_" + _FILTERED, value)
    value = _PRESIGNED_QUERY.sub(lambda match: match.group(1) + "?" + _FILTERED, value)
    value = _SENSITIVE_QUERY.sub(lambda match: match.group(1) + _FILTERED, value)
    return _redact_sql_parameters(value)


def install_error_log_redaction(target: logging.Logger | None = None) -> None:
    """Redact WARNING and ERROR records before they are written.

    With no argument this attaches to ``secureai.worker``, so a failed job
    cannot log a presigned URL. Passing a logger also covers that logger's
    current handlers. Handler filters run for records that propagate from
    child loggers; a filter on the root logger itself does not. INFO stays
    intact.
    """

    log = logging.getLogger("secureai.worker") if target is None else target
    _ensure_redacting_filter(log)
    for handler in list(log.handlers):
        _ensure_redacting_filter(handler)


class _ErrorRedactingFilter(logging.Filter):
    """Apply ``redact_text`` from WARNING up, including traceback text."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno < logging.WARNING:
            return True
        if isinstance(record.msg, str):
            record.msg = redact_text(record.msg)
        record.args = _redact_log_args(record.args)
        if record.exc_info and not record.exc_text:
            record.exc_text = redact_text(logging.Formatter().formatException(record.exc_info))
        elif isinstance(record.exc_text, str):
            record.exc_text = redact_text(record.exc_text)
        return True


def _ensure_redacting_filter(target: logging.Logger | logging.Handler) -> None:
    if any(isinstance(item, _ErrorRedactingFilter) for item in target.filters):
        return
    target.addFilter(_ErrorRedactingFilter())


def _redact_log_args(args: object) -> object:
    if isinstance(args, tuple):
        return tuple(redact_text(item) if isinstance(item, str) else item for item in args)
    if isinstance(args, dict):
        return {key: redact_text(item) if isinstance(item, str) else item for key, item in args.items()}
    return args


def _redact_sql_parameters(value: str) -> str:
    """Drop SQLAlchemy ``[parameters: ...]`` blocks.

    The block is last, and a secret may contain ``]``, so everything from the
    marker to the end of the string goes. ``hide_parameters=True`` on the
    engine avoids putting the values in the exception in the first place.
    """

    start = value.find(_SQL_PARAMETERS)
    if start < 0:
        return value
    return value[:start] + "[parameters: " + _FILTERED + "]"


def _environment(settings: Settings) -> str | None:
    if settings.sentry_environment:
        return settings.sentry_environment
    # The SDK labels a missing environment as production. A dev workstation
    # that points a DSN at itself should not show up as production.
    if settings.auth_mode == "dev":
        return "development"
    return None


def _disable_started_client() -> None:
    import sentry_sdk

    # A fake client in tests sets the flag without activating the SDK.
    # Skip the real init unless a previous call actually enabled it.
    # default_integrations stays off so this shutdown does not patch logging.
    if sentry_sdk.get_client().is_active():
        sentry_sdk.init(dsn="", default_integrations=False)


def _integrations(service: str) -> list[Any]:
    from sentry_sdk.integrations.dedupe import DedupeIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    if service == _SERVICE_API:
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        # Breadcrumbs and log events stay off. Route bugs are captured by the
        # API exception handler. Starlette still reports an explicit HTTP 500.
        return [
            StarletteIntegration(transaction_style="endpoint", failed_request_status_codes={500}),
            FastApiIntegration(transaction_style="endpoint"),
            LoggingIntegration(level=None, event_level=None, sentry_logs_level=None),
            DedupeIntegration(),
        ]
    if service == _SERVICE_WORKER:
        # The worker catches job failures and logs them. Those ERROR records
        # are the events. Sentry Logs (a separate product) stay off.
        return [
            LoggingIntegration(level=None, event_level=logging.ERROR, sentry_logs_level=None),
            DedupeIntegration(),
        ]
    raise RuntimeError(f"Unknown error reporting service {service!r}")


def _drop_frame_vars(event: dict[str, Any]) -> None:
    exception = event.get("exception")
    if not isinstance(exception, dict):
        return
    values = exception.get("values")
    if not isinstance(values, list):
        return
    for item in values:
        if not isinstance(item, dict):
            continue
        stack = item.get("stacktrace")
        if not isinstance(stack, dict):
            continue
        frames = stack.get("frames")
        if not isinstance(frames, list):
            continue
        for frame in frames:
            if isinstance(frame, dict):
                frame.pop("vars", None)


def _sensitive_key(key: str) -> bool:
    lowered = key.lower().replace("-", "_")
    return any(part in lowered for part in _SECRET_KEY_PARTS)


def _scrub_tree(value: Any) -> None:
    if isinstance(value, dict):
        for key in list(value.keys()):
            current = value[key]
            if isinstance(key, str) and _sensitive_key(key):
                value[key] = _FILTERED
                continue
            value[key] = _scrubbed_value(current)
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            value[index] = _scrubbed_value(item)


def _scrubbed_value(current: Any) -> Any:
    """Redact one event value. Tuples are copied because logentry params are tuples."""

    if isinstance(current, (bytes, bytearray)):
        return _FILTERED
    if isinstance(current, str):
        return redact_text(current)
    if isinstance(current, tuple):
        return tuple(_scrubbed_value(item) for item in current)
    if isinstance(current, (dict, list)):
        _scrub_tree(current)
    return current
