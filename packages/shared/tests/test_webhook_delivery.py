"""Outbound webhook enqueue, signature, and retry recording."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from secureai_shared.models import JobStatus
from secureai_shared.storage import new_object_key
from secureai_shared.store import MemoryJobStore
from secureai_shared.webhook_queue import MemoryWebhookQueue, build_webhook_queue
from secureai_shared.webhooks import (
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    MemoryWebhookStore,
    WebhookConfigError,
    WebhookResolverBusy,
    deliver_once,
    event_body,
    post_webhook,
    retry_delay_seconds,
    schedule_terminal,
    signature_header,
    validate_secret,
    validate_webhook_url,
)
from secureai_shared.settings import load_settings

ORG = "org_abcdef012345"
SECRET = "signing-secret-value"
URL = "https://customer.example/hooks/secureai"
WHEN = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)


def _endpoint(store: MemoryWebhookStore, *, secret: str | None = SECRET, notify_failures: bool = True) -> None:
    store.upsert_endpoint(
        org_id=ORG,
        url=URL,
        secret=secret,
        keep_secret=False,
        notify_failures=notify_failures,
    )


def _terminal(status: JobStatus, *, org_id: str | None = ORG):
    jobs = MemoryJobStore()
    created = jobs.create(
        user_id="user_dev",
        filename="clip.mp4",
        content_type="video/mp4",
        byte_size=4,
        object_key=new_object_key("user_dev", "clip.mp4"),
        org_id=org_id,
    )
    claimed = jobs.claim(created.id)
    assert claimed is not None
    if status is JobStatus.completed:
        finished = jobs.complete(created.id, prediction="fake", confidence=0.5, attempt=claimed.attempt)
    else:
        finished = jobs.fail(created.id, attempt=claimed.attempt)
    assert finished is not None
    return finished


def test_schedule_enqueues_without_posting() -> None:
    store = MemoryWebhookStore()
    queue = MemoryWebhookQueue()
    _endpoint(store)
    job = _terminal(JobStatus.completed)
    calls = {"n": 0}

    def post(url: str, body: bytes, headers: dict[str, str], timeout: float) -> int:
        del url, body, headers, timeout
        calls["n"] += 1
        return 200

    delivery_id = schedule_terminal(store, queue, job, now=WHEN)
    assert delivery_id is not None
    assert calls["n"] == 0
    assert schedule_terminal(store, queue, job, now=WHEN) == delivery_id
    assert len(store._deliveries) == 1  # noqa: SLF001
    assert deliver_once(store, queue, post=post, timeout=1, max_attempts=5, now=WHEN) is True
    assert calls["n"] == 1


def test_signed_delivery_uses_the_stored_body() -> None:
    store = MemoryWebhookStore()
    queue = MemoryWebhookQueue()
    _endpoint(store)
    job = _terminal(JobStatus.completed)
    assert schedule_terminal(store, queue, job, now=WHEN)
    seen: dict[str, object] = {}

    def post(url: str, body: bytes, headers: dict[str, str], timeout: float) -> int:
        seen["url"] = url
        seen["body"] = body
        seen["headers"] = dict(headers)
        seen["timeout"] = timeout
        return 204

    assert deliver_once(store, queue, post=post, timeout=4, max_attempts=5, now=WHEN) is True
    body = seen["body"]
    headers = seen["headers"]
    assert isinstance(body, bytes)
    assert isinstance(headers, dict)
    timestamp = int(WHEN.timestamp())
    assert headers[TIMESTAMP_HEADER] == str(timestamp)
    assert headers[SIGNATURE_HEADER] == signature_header(SECRET, timestamp, body)
    assert headers["Content-Type"] == "application/json"
    assert seen["url"] == URL
    assert seen["timeout"] == 4
    payload = json.loads(body)
    assert payload == {
        "confidence": 0.5,
        "job_id": job.id,
        "org_id": ORG,
        "prediction": "fake",
        "status": "completed",
        "timestamp": job.updated_at.astimezone(timezone.utc).isoformat(),
    }
    assert body.decode() == event_body(job)
    saved = store.delivery_for_job(job.id)
    assert saved is not None
    assert saved.status == "succeeded"
    assert saved.attempt == 1
    assert saved.last_status_code == 204
    assert saved.last_error is None


def test_unsigned_delivery_omits_the_signature() -> None:
    store = MemoryWebhookStore()
    queue = MemoryWebhookQueue()
    _endpoint(store, secret=None)
    job = _terminal(JobStatus.completed)
    schedule_terminal(store, queue, job, now=WHEN)
    seen: dict[str, dict[str, str]] = {}

    def post(url: str, body: bytes, headers: dict[str, str], timeout: float) -> int:
        del url, body, timeout
        seen["headers"] = dict(headers)
        return 200

    deliver_once(store, queue, post=post, timeout=1, max_attempts=3, now=WHEN)
    assert SIGNATURE_HEADER not in seen["headers"]
    assert TIMESTAMP_HEADER not in seen["headers"]


def test_retry_backoff_then_success() -> None:
    store = MemoryWebhookStore()
    queue = MemoryWebhookQueue()
    _endpoint(store)
    job = _terminal(JobStatus.failed)
    schedule_terminal(store, queue, job, now=WHEN)
    calls = {"n": 0}

    def post(url: str, body: bytes, headers: dict[str, str], timeout: float) -> int:
        del url, body, headers, timeout
        calls["n"] += 1
        if calls["n"] < 3:
            return 500
        return 200

    assert deliver_once(store, queue, post=post, timeout=1, max_attempts=5, now=WHEN) is True
    first = store.delivery_for_job(job.id)
    assert first is not None
    assert first.status == "pending"
    assert first.attempt == 1
    assert first.last_status_code == 500
    assert first.last_error == "HTTP 500"
    assert first.next_attempt_at == WHEN + timedelta(seconds=retry_delay_seconds(1))
    assert deliver_once(store, queue, post=post, timeout=1, max_attempts=5, now=WHEN + timedelta(seconds=1)) is False
    second_at = WHEN + timedelta(seconds=2)
    assert deliver_once(store, queue, post=post, timeout=1, max_attempts=5, now=second_at) is True
    second = store.delivery_for_job(job.id)
    assert second is not None
    assert second.attempt == 2
    assert second.status == "pending"
    assert second.next_attempt_at == second_at + timedelta(seconds=retry_delay_seconds(2))
    assert deliver_once(
        store,
        queue,
        post=post,
        timeout=1,
        max_attempts=5,
        now=second_at + timedelta(seconds=8),
    ) is True
    done = store.delivery_for_job(job.id)
    assert done is not None
    assert done.status == "succeeded"
    assert done.attempt == 3
    assert done.last_status_code == 200
    assert calls["n"] == 3


def test_attempts_are_capped_and_the_failure_is_recorded() -> None:
    store = MemoryWebhookStore()
    queue = MemoryWebhookQueue()
    _endpoint(store)
    job = _terminal(JobStatus.completed)
    schedule_terminal(store, queue, job, now=WHEN)

    def post(url: str, body: bytes, headers: dict[str, str], timeout: float) -> int:
        del url, body, headers, timeout
        raise TimeoutError("timed out")

    assert deliver_once(store, queue, post=post, timeout=1, max_attempts=2, now=WHEN) is True
    pending = store.delivery_for_job(job.id)
    assert pending is not None
    assert pending.status == "pending"
    assert pending.last_status_code is None
    assert pending.last_error is not None
    assert "timed out" in pending.last_error
    assert deliver_once(store, queue, post=post, timeout=1, max_attempts=2, now=WHEN + timedelta(seconds=2)) is True
    failed = store.delivery_for_job(job.id)
    assert failed is not None
    assert failed.status == "failed"
    assert failed.attempt == 2
    assert failed.last_status_code is None
    assert deliver_once(store, queue, post=post, timeout=1, max_attempts=2, now=WHEN + timedelta(hours=1)) is False


def test_failures_can_be_skipped_and_personal_jobs_do_not_fire() -> None:
    store = MemoryWebhookStore()
    queue = MemoryWebhookQueue()
    _endpoint(store, notify_failures=False)
    failed = _terminal(JobStatus.failed)
    assert schedule_terminal(store, queue, failed, now=WHEN) is None
    assert queue.claim(now=WHEN.timestamp()) is None
    completed = _terminal(JobStatus.completed)
    assert schedule_terminal(store, queue, completed, now=WHEN) is not None
    personal = _terminal(JobStatus.completed, org_id=None)
    assert schedule_terminal(store, queue, personal, now=WHEN) is None


def test_removed_endpoint_records_failure_without_a_post() -> None:
    store = MemoryWebhookStore()
    queue = MemoryWebhookQueue()
    _endpoint(store)
    job = _terminal(JobStatus.completed)
    schedule_terminal(store, queue, job, now=WHEN)
    store.delete_endpoint(ORG)
    calls = {"n": 0}

    def post(url: str, body: bytes, headers: dict[str, str], timeout: float) -> int:
        del url, body, headers, timeout
        calls["n"] += 1
        return 200

    deliver_once(store, queue, post=post, timeout=1, max_attempts=5, now=WHEN)
    assert calls["n"] == 0
    saved = store.delivery_for_job(job.id)
    assert saved is not None
    assert saved.status == "failed"
    assert saved.last_error == "Endpoint removed"


def test_url_and_secret_rules() -> None:
    assert validate_webhook_url(URL) == URL
    with pytest.raises(WebhookConfigError):
        validate_webhook_url("http://customer.example/hooks")
    with pytest.raises(WebhookConfigError):
        validate_webhook_url("https://user:pw@customer.example/hooks")
    with pytest.raises(WebhookConfigError):
        validate_webhook_url("https://127.0.0.1/hooks")
    with pytest.raises(WebhookConfigError):
        validate_webhook_url("https://10.1.2.3/hooks")
    with pytest.raises(WebhookConfigError):
        validate_webhook_url("https://localhost/hooks")
    with pytest.raises(WebhookConfigError):
        validate_webhook_url("https://169.254.169.254/latest")
    assert validate_secret(SECRET) == SECRET
    with pytest.raises(WebhookConfigError):
        validate_secret("short-secret")


def test_post_webhook_rejects_private_targets_before_connect() -> None:
    with pytest.raises(RuntimeError):
        post_webhook("http://customer.example/hooks", b"{}", {}, 1)
    with pytest.raises(RuntimeError):
        post_webhook("https://127.0.0.1/hooks", b"{}", {}, 1)


def test_post_webhook_connects_to_the_validated_address(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    from secureai_shared.webhooks import _PinnedHTTPSConnection

    lookups = {"n": 0}

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del host, port, args, kwargs
        lookups["n"] += 1
        if lookups["n"] == 1:
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0))]
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))]

    seen: dict[str, object] = {}
    original_init = _PinnedHTTPSConnection.__init__

    def init(
        self: object,
        host: str,
        port: int,
        *,
        addresses: list[str],
        timeout: float,
        context: object,
    ) -> None:
        seen["host"] = host
        seen["pinned"] = list(addresses)
        seen["port"] = port
        original_init(self, host, port, addresses=addresses, timeout=timeout, context=context)  # type: ignore[arg-type]

    def create_connection(address: tuple[str, int], timeout: float, source_address: object = None) -> object:
        del timeout, source_address
        seen["connected"] = address
        raise TimeoutError("stopped")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setattr(_PinnedHTTPSConnection, "__init__", init)
    with pytest.raises(TimeoutError, match="stopped"):
        post_webhook("https://customer.example/hooks", b"{}", {}, 3)
    assert lookups["n"] == 1
    assert seen["host"] == "customer.example"
    assert seen["pinned"] == ["8.8.8.8"]
    assert seen["port"] == 443
    assert seen["connected"] == ("8.8.8.8", 443)


def test_post_webhook_tries_each_validated_address_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket
    import ssl

    from secureai_shared.webhooks import _PinnedHTTPSConnection

    lookups = {"n": 0}

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del port, args, kwargs
        assert host == "customer.example"
        lookups["n"] += 1
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
        ]

    attempts: list[tuple[str, int]] = []

    class _Sock:
        def setsockopt(self, *_args: object, **_kwargs: object) -> None:
            return None

        def settimeout(self, *_args: object, **_kwargs: object) -> None:
            return None

        def close(self) -> None:
            return None

    def create_connection(
        address: tuple[str, int], timeout: float, source_address: object = None
    ) -> object:
        del timeout, source_address
        attempts.append(address)
        if address[0] == "1.1.1.1":
            raise OSError("unreachable")
        return _Sock()

    seen: dict[str, object] = {}
    original_init = _PinnedHTTPSConnection.__init__

    def init(
        self: object,
        host: str,
        port: int,
        *,
        addresses: list[str],
        timeout: float,
        context: object,
    ) -> None:
        seen["host"] = host
        seen["addresses"] = list(addresses)
        original_init(self, host, port, addresses=addresses, timeout=timeout, context=context)  # type: ignore[arg-type]

    def wrap_socket(self: object, sock: object, *args: object, **kwargs: object) -> object:
        del self, sock, args
        seen["sni"] = kwargs.get("server_hostname")
        raise TimeoutError("tls stopped")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setattr(_PinnedHTTPSConnection, "__init__", init)
    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", wrap_socket)
    with pytest.raises(TimeoutError, match="tls stopped"):
        post_webhook("https://customer.example/hooks", b"{}", {}, 3)
    assert lookups["n"] == 1
    assert seen["host"] == "customer.example"
    assert seen["addresses"] == ["1.1.1.1", "8.8.8.8"]
    assert attempts == [("1.1.1.1", 443), ("8.8.8.8", 443)]
    assert seen["sni"] == "customer.example"


def test_post_webhook_stops_after_the_first_address_connects(monkeypatch: pytest.MonkeyPatch) -> None:
    """A certificate failure is not a connect failure and does not try the next address."""

    import socket
    import ssl

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del host, port, args, kwargs
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
        ]

    attempts: list[str] = []

    class _Sock:
        def setsockopt(self, *_args: object, **_kwargs: object) -> None:
            return None

        def settimeout(self, *_args: object, **_kwargs: object) -> None:
            return None

        def close(self) -> None:
            return None

    def create_connection(
        address: tuple[str, int], timeout: float, source_address: object = None
    ) -> object:
        del timeout, source_address
        attempts.append(address[0])
        return _Sock()

    def wrap_socket(self: object, sock: object, *args: object, **kwargs: object) -> object:
        del self, sock, args, kwargs
        raise ssl.SSLCertVerificationError("certificate verify failed")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", wrap_socket)
    with pytest.raises(ssl.SSLCertVerificationError, match="certificate verify failed") as raised:
        post_webhook("https://customer.example/hooks", b"{}", {}, 1)
    assert type(raised.value) is ssl.SSLCertVerificationError
    assert attempts == ["1.1.1.1"]


def test_post_webhook_shares_one_connect_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Later addresses receive only the time left, then the socket gets the full timeout."""

    import socket
    import ssl

    from secureai_shared import webhooks as webhook_module

    clock = {"now": 1_000.0}

    def monotonic() -> float:
        return clock["now"]

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del host, port, args, kwargs
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("9.9.9.9", 0)),
        ]

    attempts: list[tuple[str, float]] = []

    class _Sock:
        def __init__(self) -> None:
            self.timeouts: list[float] = []

        def setsockopt(self, *_args: object, **_kwargs: object) -> None:
            return None

        def settimeout(self, value: float) -> None:
            self.timeouts.append(value)

        def close(self) -> None:
            return None

    opened: list[_Sock] = []

    def create_connection(
        address: tuple[str, int], timeout: float, source_address: object = None
    ) -> object:
        del source_address
        attempts.append((address[0], timeout))
        clock["now"] += 0.4
        if address[0] != "9.9.9.9":
            raise OSError(address[0])
        sock = _Sock()
        opened.append(sock)
        return sock

    def wrap_socket(self: object, sock: object, *args: object, **kwargs: object) -> object:
        del self, sock, args, kwargs
        raise ssl.SSLCertVerificationError("certificate verify failed")

    monkeypatch.setattr(webhook_module.time, "monotonic", monotonic)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", wrap_socket)
    with pytest.raises(ssl.SSLCertVerificationError, match="certificate verify failed"):
        post_webhook("https://customer.example/hooks", b"{}", {}, 1)
    assert [item[0] for item in attempts] == ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
    assert attempts[0][1] == pytest.approx(1.0)
    assert attempts[1][1] == pytest.approx(0.6)
    assert attempts[2][1] == pytest.approx(0.2)
    assert opened[0].timeouts == [1.0]


def test_post_webhook_stops_when_the_connect_budget_is_spent(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    from secureai_shared import webhooks as webhook_module

    clock = {"now": 500.0}

    def monotonic() -> float:
        return clock["now"]

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del host, port, args, kwargs
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
        ]

    attempts: list[str] = []

    def create_connection(
        address: tuple[str, int], timeout: float, source_address: object = None
    ) -> object:
        del source_address
        attempts.append(address[0])
        clock["now"] += timeout
        raise TimeoutError("slow")

    monkeypatch.setattr(webhook_module.time, "monotonic", monotonic)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    with pytest.raises(TimeoutError, match="slow") as raised:
        post_webhook("https://customer.example/hooks", b"{}", {}, 1)
    assert attempts == ["1.1.1.1"]
    assert "did not resolve" not in str(raised.value)


def test_post_webhook_does_not_connect_when_the_budget_is_already_spent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import socket

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del host, port, args, kwargs
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 0))]

    def create_connection(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("connected")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    with pytest.raises(TimeoutError, match="webhook connect timed out") as raised:
        post_webhook("https://customer.example/hooks", b"{}", {}, 0)
    assert "did not resolve" not in str(raised.value)


def test_pinned_connect_without_addresses_is_not_a_resolve_failure() -> None:
    import ssl

    from secureai_shared.webhooks import _PinnedHTTPSConnection

    connection = _PinnedHTTPSConnection(
        "customer.example",
        443,
        addresses=[],
        timeout=1,
        context=ssl.create_default_context(),
    )
    with pytest.raises(OSError, match="no pinned address") as raised:
        connection.connect()
    assert "did not resolve" not in str(raised.value)


def test_pinned_connect_accepts_the_default_timeout_sentinel(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``http.client`` stores ``socket._GLOBAL_DEFAULT_TIMEOUT`` when timeout is omitted.

    That sentinel is not a number. Connecting with it must not raise
    TypeError. It follows the same path as ``None``: no shared deadline,
    and the TCP attempt blocks.
    """

    import socket
    import ssl

    from secureai_shared.webhooks import _PinnedHTTPSConnection

    seen: dict[str, object] = {}

    class _Sock:
        def __init__(self) -> None:
            self.timeouts: list[object] = []

        def setsockopt(self, *_args: object, **_kwargs: object) -> None:
            return None

        def settimeout(self, value: object) -> None:
            self.timeouts.append(value)

        def close(self) -> None:
            return None

    def create_connection(
        address: tuple[str, int],
        timeout: object = socket._GLOBAL_DEFAULT_TIMEOUT,
        source_address: object = None,
    ) -> object:
        del source_address
        seen["address"] = address
        seen["timeout"] = timeout
        sock = _Sock()
        seen["sock"] = sock
        return sock

    def wrap_socket(self: object, sock: object, *args: object, **kwargs: object) -> object:
        del self, args, kwargs
        return sock

    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", wrap_socket)
    connection = _PinnedHTTPSConnection(
        "customer.example",
        443,
        addresses=["1.1.1.1"],
        timeout=socket._GLOBAL_DEFAULT_TIMEOUT,  # type: ignore[arg-type]
        context=ssl.create_default_context(),
    )
    assert connection.timeout is socket._GLOBAL_DEFAULT_TIMEOUT
    connection.connect()
    assert seen["address"] == ("1.1.1.1", 443)
    assert seen["timeout"] is None
    sock = seen["sock"]
    assert isinstance(sock, _Sock)
    assert sock.timeouts == []


def test_post_webhook_resolve_failure_says_it_did_not_resolve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import socket

    def getaddrinfo(*_args: object, **_kwargs: object) -> list[tuple]:
        raise socket.gaierror(socket.EAI_NONAME, "Name or service not known")

    def create_connection(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("connected")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    with pytest.raises(RuntimeError, match="webhook host did not resolve"):
        post_webhook("https://customer.example/hooks", b"{}", {}, 1)


def test_post_webhook_raises_the_last_connect_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del host, port, args, kwargs
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("1.1.1.1", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
        ]

    attempts: list[str] = []

    def create_connection(
        address: tuple[str, int], timeout: float, source_address: object = None
    ) -> object:
        del timeout, source_address
        attempts.append(address[0])
        raise ConnectionRefusedError(address[0])

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    with pytest.raises(ConnectionRefusedError, match="8.8.8.8"):
        post_webhook("https://customer.example/hooks", b"{}", {}, 1)
    assert attempts == ["1.1.1.1", "8.8.8.8"]


def test_post_webhook_rejects_a_private_address_in_the_same_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del host, port, args, kwargs
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0)),
        ]

    def create_connection(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("connected")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    with pytest.raises(RuntimeError, match="not a public"):
        post_webhook("https://customer.example/hooks", b"{}", {}, 1)


def _wait_for_dns_threads() -> None:
    import threading
    import time

    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        live = [
            thread
            for thread in threading.enumerate()
            if thread.name == "secureai-webhook-dns" and thread.is_alive()
        ]
        if not live:
            return
        time.sleep(0.01)
    raise AssertionError("webhook dns thread still running")


def test_dns_time_comes_out_of_the_connect_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """Lookup time is part of the TCP budget. TLS still gets the original timeout."""

    import socket
    import ssl

    from secureai_shared import webhooks as webhook_module

    clock = {"now": 100.0}

    def monotonic() -> float:
        return clock["now"]

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del host, port, args, kwargs
        clock["now"] += 0.3
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0))]

    attempts: list[float] = []

    class _Sock:
        def __init__(self) -> None:
            self.timeouts: list[float] = []

        def setsockopt(self, *_args: object, **_kwargs: object) -> None:
            return None

        def settimeout(self, value: float) -> None:
            self.timeouts.append(value)

        def close(self) -> None:
            return None

    opened: list[_Sock] = []

    def create_connection(
        address: tuple[str, int], timeout: float, source_address: object = None
    ) -> object:
        del address, source_address
        attempts.append(timeout)
        clock["now"] += 0.1
        sock = _Sock()
        opened.append(sock)
        return sock

    def wrap_socket(self: object, sock: object, *args: object, **kwargs: object) -> object:
        del self, sock, args, kwargs
        raise ssl.SSLCertVerificationError("certificate verify failed")

    monkeypatch.setattr(webhook_module.time, "monotonic", monotonic)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    monkeypatch.setattr(ssl.SSLContext, "wrap_socket", wrap_socket)
    with pytest.raises(ssl.SSLCertVerificationError, match="certificate verify failed"):
        post_webhook("https://customer.example/hooks", b"{}", {}, 1)
    assert attempts == [pytest.approx(0.7)]
    assert opened[0].timeouts == [1.0]


def test_dns_that_uses_the_whole_timeout_does_not_connect(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    from secureai_shared import webhooks as webhook_module

    clock = {"now": 50.0}

    def monotonic() -> float:
        return clock["now"]

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del host, port, args, kwargs
        clock["now"] += 1
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0))]

    def create_connection(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("connected")

    monkeypatch.setattr(webhook_module.time, "monotonic", monotonic)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    with pytest.raises(TimeoutError, match="webhook connect timed out"):
        post_webhook("https://customer.example/hooks", b"{}", {}, 1)


def test_stuck_dns_returns_within_the_timeout_and_counts_as_an_attempt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import socket
    import threading
    import time

    release = threading.Event()
    seen: dict[str, bool] = {}

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del host, port, args, kwargs
        seen["daemon"] = threading.current_thread().daemon
        release.wait(2)
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0))]

    def create_connection(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("connected")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    store = MemoryWebhookStore()
    queue = MemoryWebhookQueue()
    _endpoint(store)
    job = _terminal(JobStatus.completed)
    schedule_terminal(store, queue, job, now=WHEN)
    started = time.monotonic()
    try:
        assert (
            deliver_once(store, queue, post=post_webhook, timeout=0.2, max_attempts=5, now=WHEN)
            is True
        )
        elapsed = time.monotonic() - started
    finally:
        release.set()
        _wait_for_dns_threads()
    assert seen["daemon"] is True
    assert elapsed < 1.0
    saved = store.delivery_for_job(job.id)
    assert saved is not None
    assert saved.status == "pending"
    assert saved.attempt == 1
    assert saved.last_error is not None
    assert "webhook DNS timed out" in saved.last_error
    assert saved.next_attempt_at == WHEN + timedelta(seconds=retry_delay_seconds(1))


def test_busy_resolver_defers_without_counting_an_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket
    import time

    from secureai_shared import webhooks as webhook_module

    def getaddrinfo(*_args: object, **_kwargs: object) -> list[tuple]:
        raise AssertionError("resolved while the resolver was busy")

    def create_connection(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("connected")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    store = MemoryWebhookStore()
    queue = MemoryWebhookQueue()
    _endpoint(store)
    job = _terminal(JobStatus.completed)
    schedule_terminal(store, queue, job, now=WHEN)
    held = 0
    try:
        for _ in range(webhook_module._DNS_LOOKUP_SLOTS):
            assert webhook_module._DNS_SLOTS.acquire(blocking=False)
            held += 1
        started = time.monotonic()
        assert (
            deliver_once(store, queue, post=post_webhook, timeout=5, max_attempts=2, now=WHEN)
            is True
        )
        assert time.monotonic() - started < 1.0
        saved = store.delivery_for_job(job.id)
        assert saved is not None
        assert saved.attempt == 0
        assert saved.status == "pending"
        assert saved.last_error == "DNS resolver is busy (1)"
        assert webhook_module._DNS_KEY_IN_FLIGHT == {}
        assert saved.delivering_until is None
        assert saved.next_attempt_at == WHEN + timedelta(seconds=webhook_module._DNS_BUSY_DELAY_SECONDS)
        assert (
            deliver_once(store, queue, post=post_webhook, timeout=5, max_attempts=2, now=WHEN)
            is False
        )
    finally:
        for _ in range(held):
            webhook_module._DNS_SLOTS.release()

    def post(url: str, body: bytes, headers: dict[str, str], timeout: float) -> int:
        del url, body, headers, timeout
        return 204

    later = WHEN + timedelta(seconds=webhook_module._DNS_BUSY_DELAY_SECONDS)
    assert deliver_once(store, queue, post=post, timeout=5, max_attempts=2, now=later) is True
    done = store.delivery_for_job(job.id)
    assert done is not None
    assert done.status == "succeeded"
    assert done.attempt == 1
    assert done.last_status_code == 204


def test_dns_slot_bounds_match_the_delivery_contract() -> None:
    from secureai_shared import webhooks as webhook_module

    assert webhook_module._DNS_LOOKUP_SLOTS == 2
    assert webhook_module._DNS_PER_KEY_SLOTS == 1
    assert webhook_module._DNS_BUSY_DELAY_SECONDS == 1.0
    assert webhook_module._DNS_BUSY_DEFERRAL_LIMIT == 30


def test_busy_deferral_count_ignores_other_errors() -> None:
    from secureai_shared import webhooks as webhook_module

    assert webhook_module._busy_deferrals_used(None) == 0
    assert webhook_module._busy_deferrals_used("TimeoutError: webhook DNS timed out") == 0
    assert webhook_module._busy_deferrals_used("DNS resolver is busy") == 0
    assert webhook_module._busy_deferrals_used("DNS resolver is busy (2)") == 2
    assert webhook_module._busy_deferrals_used("DNS resolver is busy (2) extra") == 0
    assert webhook_module._busy_deferrals_used("DNS resolver is busy ()") == 0


def test_busy_deferrals_count_as_attempts_after_the_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    """A resolver that never frees a slot cannot defer the same row forever."""

    import socket

    from secureai_shared import webhooks as webhook_module

    monkeypatch.setattr(webhook_module, "_DNS_BUSY_DEFERRAL_LIMIT", 2)

    def getaddrinfo(*_args: object, **_kwargs: object) -> list[tuple]:
        raise AssertionError("resolved while the resolver was busy")

    def create_connection(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("connected")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    store = MemoryWebhookStore()
    queue = MemoryWebhookQueue()
    _endpoint(store)
    job = _terminal(JobStatus.completed)
    schedule_terminal(store, queue, job, now=WHEN)
    held = 0
    try:
        for _ in range(webhook_module._DNS_LOOKUP_SLOTS):
            assert webhook_module._DNS_SLOTS.acquire(blocking=False)
            held += 1
        clock = WHEN
        for expected in (1, 2):
            assert (
                deliver_once(store, queue, post=post_webhook, timeout=5, max_attempts=2, now=clock)
                is True
            )
            saved = store.delivery_for_job(job.id)
            assert saved is not None
            assert saved.attempt == 0
            assert saved.status == "pending"
            assert saved.last_error == f"DNS resolver is busy ({expected})"
            assert saved.next_attempt_at == clock + timedelta(seconds=1)
            clock = saved.next_attempt_at
        assert (
            deliver_once(store, queue, post=post_webhook, timeout=5, max_attempts=2, now=clock)
            is True
        )
        counted = store.delivery_for_job(job.id)
        assert counted is not None
        assert counted.attempt == 1
        assert counted.status == "pending"
        assert counted.last_error == "DNS resolver is busy (2)"
        assert counted.next_attempt_at == clock + timedelta(seconds=retry_delay_seconds(1))
        clock = counted.next_attempt_at
        assert (
            deliver_once(store, queue, post=post_webhook, timeout=5, max_attempts=2, now=clock)
            is True
        )
        failed = store.delivery_for_job(job.id)
        assert failed is not None
        assert failed.status == "failed"
        assert failed.attempt == 2
        assert failed.last_error == "DNS resolver is busy (2)"
        assert deliver_once(store, queue, post=post_webhook, timeout=5, max_attempts=2, now=clock) is False
    finally:
        for _ in range(held):
            webhook_module._DNS_SLOTS.release()
        assert webhook_module._DNS_KEY_IN_FLIGHT == {}


def test_one_org_cannot_hold_both_dns_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    """A stuck lookup for one workspace leaves the other process slot free."""

    import socket
    import threading

    from secureai_shared import webhooks as webhook_module

    release = threading.Event()
    entered: list[str] = []
    entered_lock = threading.Lock()
    first = threading.Event()
    second = threading.Event()

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del port, args, kwargs
        with entered_lock:
            entered.append(host)
            count = len(entered)
        if count == 1:
            first.set()
        if count >= 2:
            second.set()
        release.wait()
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0))]

    def create_connection(*_args: object, **_kwargs: object) -> object:
        raise TimeoutError("stopped")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)

    store = MemoryWebhookStore()
    queue = MemoryWebhookQueue()
    org_a = ORG
    org_b = "org_bbbbbbbbbbbb"
    org_c = "org_cccccccccccc"
    for org_id in (org_a, org_b, org_c):
        store.upsert_endpoint(
            org_id=org_id,
            url="https://customer.example/hooks/secureai",
            secret=None,
            keep_secret=False,
            notify_failures=True,
        )
    job_a = _terminal(JobStatus.completed, org_id=org_a)
    job_a2 = _terminal(JobStatus.completed, org_id=org_a)
    job_b = _terminal(JobStatus.completed, org_id=org_b)
    job_c = _terminal(JobStatus.completed, org_id=org_c)
    schedule_terminal(store, queue, job_a, now=WHEN)
    errors: list[BaseException] = []

    def deliver() -> None:
        try:
            deliver_once(store, queue, post=post_webhook, timeout=0.4, max_attempts=5, now=WHEN)
        except BaseException as exc:
            errors.append(exc)

    worker_a = threading.Thread(target=deliver, name="dns-fairness-a")
    worker_b = threading.Thread(target=deliver, name="dns-fairness-b")
    try:
        worker_a.start()
        assert first.wait(2)
        assert webhook_module._DNS_KEY_IN_FLIGHT == {f"org:{org_a}": 1}
        # The process still has a free slot. Org A cannot take it.
        assert webhook_module._DNS_SLOTS.acquire(blocking=False)
        webhook_module._DNS_SLOTS.release()
        schedule_terminal(store, queue, job_a2, now=WHEN)
        assert deliver_once(store, queue, post=post_webhook, timeout=5, max_attempts=5, now=WHEN) is True
        saved_a2 = store.delivery_for_job(job_a2.id)
        assert saved_a2 is not None
        assert saved_a2.attempt == 0
        assert saved_a2.status == "pending"
        assert saved_a2.last_error == "DNS resolver is busy (1)"
        assert entered == ["customer.example"]

        schedule_terminal(store, queue, job_b, now=WHEN)
        worker_b.start()
        assert second.wait(2)
        assert entered == ["customer.example", "customer.example"]
        assert webhook_module._DNS_KEY_IN_FLIGHT == {f"org:{org_a}": 1, f"org:{org_b}": 1}

        schedule_terminal(store, queue, job_c, now=WHEN)
        assert deliver_once(store, queue, post=post_webhook, timeout=5, max_attempts=5, now=WHEN) is True
        saved_c = store.delivery_for_job(job_c.id)
        assert saved_c is not None
        assert saved_c.attempt == 0
        assert saved_c.last_error == "DNS resolver is busy (1)"
        assert entered == ["customer.example", "customer.example"]
    finally:
        release.set()
        worker_a.join(3)
        if worker_b.ident is not None:
            worker_b.join(3)
        _wait_for_dns_threads()
    assert errors == []
    assert webhook_module._DNS_KEY_IN_FLIGHT == {}


def test_same_hostname_takes_one_slot_when_there_is_no_org(monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct posts have no organization, so the hostname is the fairness key."""

    import socket
    import threading
    import time

    from secureai_shared import webhooks as webhook_module

    release = threading.Event()
    entered: list[str] = []
    entered_lock = threading.Lock()
    first = threading.Event()
    second = threading.Event()

    def getaddrinfo(host: str, port: object, *args: object, **kwargs: object) -> list[tuple]:
        del port, args, kwargs
        with entered_lock:
            entered.append(host)
            count = len(entered)
        if count == 1:
            first.set()
        if count >= 2:
            second.set()
        release.wait()
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("8.8.8.8", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    assert webhook_module._DNS_TENANT.get() == ""
    errors: list[BaseException] = []

    def lookup(host: str, timeout: float) -> None:
        try:
            webhook_module._getaddrinfo_bounded(host, timeout)
        except BaseException as exc:
            errors.append(exc)

    first_thread = threading.Thread(target=lookup, args=("Customer.Example.", 2))
    other_thread = threading.Thread(target=lookup, args=("other.example", 2))
    try:
        first_thread.start()
        assert first.wait(2)
        assert webhook_module._DNS_KEY_IN_FLIGHT == {"host:customer.example": 1}
        started = time.monotonic()
        with pytest.raises(WebhookResolverBusy):
            webhook_module._getaddrinfo_bounded("customer.example", 2)
        assert time.monotonic() - started < 0.5
        assert webhook_module._DNS_SLOTS.acquire(blocking=False)
        webhook_module._DNS_SLOTS.release()
        other_thread.start()
        assert second.wait(2)
        assert entered == ["Customer.Example.", "other.example"]
        with pytest.raises(WebhookResolverBusy):
            webhook_module._getaddrinfo_bounded("third.example", 2)
        assert entered == ["Customer.Example.", "other.example"]
    finally:
        release.set()
        first_thread.join(3)
        if other_thread.ident is not None:
            other_thread.join(3)
        _wait_for_dns_threads()
    assert errors == []
    assert webhook_module._DNS_KEY_IN_FLIGHT == {}


def test_post_webhook_does_not_resolve_a_public_ip_literal(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    def getaddrinfo(*_args: object, **_kwargs: object) -> list[tuple]:
        raise AssertionError("resolved")

    seen: dict[str, object] = {}

    def create_connection(address: tuple[str, int], timeout: float, source_address: object = None) -> object:
        del timeout, source_address
        seen["address"] = address
        raise TimeoutError("stopped")

    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    monkeypatch.setattr(socket, "create_connection", create_connection)
    with pytest.raises(TimeoutError, match="stopped"):
        post_webhook("https://8.8.8.8/hooks", b"{}", {}, 1)
    assert seen["address"] == ("8.8.8.8", 443)


def test_upsert_retries_when_a_concurrent_insert_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from secureai_shared.db import Base
    from secureai_shared.webhooks import PostgresWebhookStore

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    store = PostgresWebhookStore(engine=engine)
    created = store.upsert_endpoint(
        org_id="org_race",
        url=URL,
        secret=SECRET,
        keep_secret=False,
        notify_failures=True,
    )
    assert created.secret == SECRET
    original = Session.get
    state = {"hide": True}

    def get(self: Session, entity: object, ident: object, *args: object, **kwargs: object) -> object:
        if state["hide"] and getattr(entity, "__name__", "") == "WebhookEndpointRow":
            state["hide"] = False
            return None
        return original(self, entity, ident, *args, **kwargs)

    monkeypatch.setattr(Session, "get", get)
    saved = store.upsert_endpoint(
        org_id="org_race",
        url="https://customer.example/hooks/next",
        secret=None,
        keep_secret=True,
        notify_failures=None,
    )
    assert saved.url == "https://customer.example/hooks/next"
    assert saved.secret == SECRET
    again = store.get_endpoint("org_race")
    assert again is not None
    assert again.secret == SECRET


def test_webhook_queue_follows_the_job_backend() -> None:
    settings = load_settings(
        {
            "AUTH_MODE": "dev",
            "DATABASE_URL": "postgresql+psycopg://unused/unused",
            "QUEUE_BACKEND": "memory",
            "QUEUE_KEY": "secureai:jobs",
        },
        role="worker",
    )
    assert isinstance(build_webhook_queue(settings), MemoryWebhookQueue)


def test_redis_webhook_queue_claims_only_due_ids() -> None:
    url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    try:
        import redis

        client = redis.Redis.from_url(url, decode_responses=True)
        client.ping()
    except Exception as exc:
        if os.environ.get("REQUIRE_SERVICES") == "1":
            pytest.fail(f"redis unavailable: {exc}")
        pytest.skip(f"redis unavailable: {exc}")
    from secureai_shared.webhook_queue import RedisWebhookQueue

    key = "secureai:webhooks:unit"
    client.delete(key)
    queue = RedisWebhookQueue(url, key=key, client=client)
    queue.publish("whd_later", available_at=500.0)
    queue.publish("whd_now", available_at=10.0)
    assert queue.claim(now=20) == "whd_now"
    assert queue.claim(now=20) is None
    assert queue.claim(now=500) == "whd_later"
    client.delete(key)


def test_postgres_endpoint_round_trip() -> None:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://secureai:secureai@127.0.0.1:5432/secureai",
    )
    try:
        from sqlalchemy.orm import Session

        from secureai_shared.db import Base, OrganizationRow
        from secureai_shared.webhooks import PostgresWebhookStore

        probe = PostgresWebhookStore(url)
        with probe.engine.connect() as connection:
            connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS secureai_webhook_test")
            connection.commit()
        probe.engine.dispose()
        schema_url = url + ("&" if "?" in url else "?") + "options=-csearch_path%3Dsecureai_webhook_test"
        store = PostgresWebhookStore(schema_url)
        Base.metadata.drop_all(store.engine)
        Base.metadata.create_all(store.engine)
    except Exception as exc:
        if os.environ.get("REQUIRE_SERVICES") == "1":
            pytest.fail(f"postgres unavailable: {exc}")
        pytest.skip(f"postgres unavailable: {exc}")

    now = datetime.now(timezone.utc)
    with Session(store.engine) as session:
        session.add(
            OrganizationRow(
                id=ORG,
                name="Studio",
                plan="free",
                created_at=now,
                updated_at=now,
            )
        )
        session.commit()
    saved = store.upsert_endpoint(
        org_id=ORG,
        url=URL,
        secret=SECRET,
        keep_secret=False,
        notify_failures=True,
    )
    assert saved.secret == SECRET
    kept = store.upsert_endpoint(
        org_id=ORG,
        url="https://customer.example/hooks/next",
        secret=None,
        keep_secret=True,
        notify_failures=None,
    )
    assert kept.secret == SECRET
    assert kept.url.endswith("/next")
    job = _terminal(JobStatus.completed)
    created = store.create_delivery(org_id=ORG, job_id=job.id, payload=event_body(job), now=WHEN)
    assert created is not None
    assert store.create_delivery(org_id=ORG, job_id=job.id, payload="{}", now=WHEN) is None
    assert store.delivery_for_job(job.id) is not None
    claimed = store.begin_attempt(created.id, now=WHEN, lease_seconds=30)
    assert claimed is not None
    assert claimed.claim_token
    recorded = store.record_result(
        created.id,
        claim_token=claimed.claim_token,
        status="succeeded",
        attempt=1,
        last_status_code=200,
        last_error=None,
        next_attempt_at=WHEN,
        now=WHEN,
    )
    assert recorded is not None
    assert recorded.status == "succeeded"
    assert store.delete_endpoint(ORG) is True
    assert store.get_endpoint(ORG) is None
