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

    def init(self: object, host: str, port: int, *, address: str, timeout: float, context: object) -> None:
        seen["host"] = host
        seen["pinned"] = address
        seen["port"] = port
        original_init(self, host, port, address=address, timeout=timeout, context=context)  # type: ignore[arg-type]

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
    assert seen["pinned"] == "8.8.8.8"
    assert seen["port"] == 443
    assert seen["connected"] == ("8.8.8.8", 443)


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
