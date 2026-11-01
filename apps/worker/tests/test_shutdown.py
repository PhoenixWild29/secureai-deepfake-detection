"""SIGTERM finishes the popped job and the webhook POST already in progress."""

from __future__ import annotations

import json
import logging
import math
import os
import signal
import threading
import time
from datetime import datetime, timezone
from inspect import signature
from pathlib import Path
from types import SimpleNamespace

import pytest

from secureai_shared.models import JobStatus
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.reporting import flush_error_reporting
from secureai_shared.settings import Settings
from secureai_shared.storage import FileSystemStorage, new_object_key
from secureai_shared.store import MemoryJobStore
from secureai_shared.webhook_queue import MemoryWebhookQueue
from secureai_shared.webhooks import MemoryWebhookStore
from worker.__main__ import (
    DRAIN_MARGIN_SECONDS,
    DEFAULT_POLL_SECONDS,
    SENTRY_FLUSH_SECONDS,
    WEBHOOK_JOIN_MARGIN_SECONDS,
    WEBHOOK_LEASE_MARGIN_SECONDS,
    _serve_webhooks,
    run,
    shutdown_drain_seconds,
    webhook_delivery_lease_seconds,
    webhook_shutdown_join_seconds,
    warn_if_detector_timeout_exceeds_drain,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKER_ROOT = Path(__file__).resolve().parents[1]


def _live_webhook_threads() -> list[threading.Thread]:
    return [
        thread
        for thread in threading.enumerate()
        if thread.name == "secureai-webhooks" and thread.is_alive()
    ]


def test_shutdown_drain_covers_poll_detection_and_sentry_flush() -> None:
    flush_default = signature(flush_error_reporting).parameters["timeout"].default
    assert flush_default == SENTRY_FLUSH_SECONDS
    assert Settings.detector_timeout_seconds == 60.0
    assert shutdown_drain_seconds() == math.ceil(
        DEFAULT_POLL_SECONDS
        + Settings.detector_timeout_seconds
        + SENTRY_FLUSH_SECONDS
        + DRAIN_MARGIN_SECONDS
    )
    # deploy/railway/README.md and worker.railway.json both use this number.
    assert shutdown_drain_seconds() == 75


def test_webhook_shutdown_join_fits_in_the_platform_drain() -> None:
    # load_settings caps WEBHOOK_TIMEOUT_SECONDS at 30. An idle SIGTERM
    # spends the current poll, then this join, then the Sentry flush.
    maximum_webhook_timeout = 30.0
    idle = (
        DEFAULT_POLL_SECONDS
        + webhook_shutdown_join_seconds(maximum_webhook_timeout)
        + SENTRY_FLUSH_SECONDS
    )
    assert idle <= shutdown_drain_seconds()
    assert shutdown_drain_seconds() == 75
    assert webhook_shutdown_join_seconds(Settings.webhook_timeout_seconds) == (
        2 * Settings.webhook_timeout_seconds + WEBHOOK_JOIN_MARGIN_SECONDS
    )
    # The lease is counted from the claim. At the maximum timeout it is 75
    # seconds and the join is 62. Idle shutdown stays 5 + 62 + 2 = 69.
    assert webhook_delivery_lease_seconds(maximum_webhook_timeout) == 75.0
    assert webhook_shutdown_join_seconds(maximum_webhook_timeout) == 62.0
    assert idle == 69.0
    assert webhook_delivery_lease_seconds(maximum_webhook_timeout) >= (
        webhook_shutdown_join_seconds(maximum_webhook_timeout)
    )


@pytest.mark.parametrize("timeout", [10.0, 13.0, 14.0, 30.0])
def test_delivery_lease_covers_the_shutdown_join(timeout: float) -> None:
    # t+15 covers the join 2t+2 only while t is at most 13. Above that,
    # including the allowed maximum of 30, the claim expired during the join.
    lease = webhook_delivery_lease_seconds(timeout)
    join_for = webhook_shutdown_join_seconds(timeout)
    previous_lease = timeout + WEBHOOK_LEASE_MARGIN_SECONDS
    assert lease == 2 * timeout + WEBHOOK_LEASE_MARGIN_SECONDS
    assert join_for == 2 * timeout + WEBHOOK_JOIN_MARGIN_SECONDS
    assert lease >= join_for
    assert lease - join_for == WEBHOOK_LEASE_MARGIN_SECONDS - WEBHOOK_JOIN_MARGIN_SECONDS
    if timeout > 13:
        assert previous_lease < join_for
    else:
        assert previous_lease >= join_for


@pytest.mark.parametrize("timeout", [10.0, 14.0, 30.0])
def test_serve_webhooks_claims_with_the_lease_that_covers_the_join(
    timeout: float,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, float] = {}
    stop = {"flag": False}

    def deliver_once(*_args: object, **kwargs: object) -> bool:
        lease = kwargs["lease_seconds"]
        posted_timeout = kwargs["timeout"]
        assert isinstance(lease, (int, float))
        assert isinstance(posted_timeout, (int, float))
        seen["lease_seconds"] = float(lease)
        seen["timeout"] = float(posted_timeout)
        stop["flag"] = True
        return False

    monkeypatch.setattr("worker.__main__.deliver_once", deliver_once)
    settings = SimpleNamespace(webhook_timeout_seconds=timeout, webhook_max_attempts=5)
    _serve_webhooks(stop, None, None, settings)  # type: ignore[arg-type]
    assert seen["timeout"] == timeout
    assert seen["lease_seconds"] == webhook_delivery_lease_seconds(timeout)
    assert seen["lease_seconds"] >= webhook_shutdown_join_seconds(timeout)


@pytest.mark.parametrize("timeout", [60.0, 59.0, 1.0])
def test_no_drain_warning_at_or_below_the_default_detector_timeout(
    timeout: float,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="secureai.worker"):
        warn_if_detector_timeout_exceeds_drain(timeout)
    assert caplog.records == []


@pytest.mark.parametrize(
    ("timeout", "delta"),
    [(90.0, "30"), (60.5, "0.5")],
)
def test_drain_warning_names_the_delta_above_the_default_timeout(
    timeout: float,
    delta: str,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="secureai.worker"):
        warn_if_detector_timeout_exceeds_drain(timeout)
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.WARNING
    assert record.name == "secureai.worker"
    message = record.getMessage()
    assert f"DETECTOR_TIMEOUT_SECONDS={timeout:g}" in message
    assert "drain budget may be short" in message
    assert f"drainingSeconds={shutdown_drain_seconds()}" in message
    assert f"Raise drainingSeconds by {delta}" in message
    assert shutdown_drain_seconds() == 75


def _prepare_idle_worker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("QUEUE_BACKEND", "memory")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    monkeypatch.setattr("worker.__main__.PostgresJobStore", lambda url: MemoryJobStore())
    monkeypatch.setattr("worker.__main__.build_queue", lambda settings: MemoryJobQueue())
    monkeypatch.setattr(
        "worker.__main__.build_storage",
        lambda settings: FileSystemStorage(tmp_path),
    )


@pytest.mark.parametrize("timeout", [None, "60", "60.0"])
def test_worker_startup_does_not_warn_at_the_default_detector_timeout(
    timeout: str | None,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _prepare_idle_worker(monkeypatch, tmp_path)
    if timeout is None:
        monkeypatch.delenv("DETECTOR_TIMEOUT_SECONDS", raising=False)
    else:
        monkeypatch.setenv("DETECTOR_TIMEOUT_SECONDS", timeout)
    with caplog.at_level(logging.WARNING, logger="secureai.worker"):
        assert run(["--once"]) == 0
    assert shutdown_drain_seconds() == 75
    assert not any("drain budget may be short" in record.getMessage() for record in caplog.records)


def test_worker_startup_warns_once_when_detector_timeout_exceeds_drain(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    _prepare_idle_worker(monkeypatch, tmp_path)
    monkeypatch.setenv("DETECTOR_TIMEOUT_SECONDS", "90")
    polls = {"n": 0}

    class StoppingQueue(MemoryJobQueue):
        def consume(self, timeout: float = 0) -> str | None:
            del timeout
            polls["n"] += 1
            if polls["n"] >= 3:
                raise RuntimeError("stop-polling")
            return None

    monkeypatch.setattr("worker.__main__.build_queue", lambda settings: StoppingQueue())
    # The drain warning is before the poll loop. A warning inside the loop
    # would fire on each of these empty reads.
    monkeypatch.setattr("worker.__main__.threading.Thread.start", lambda _self: None)
    with caplog.at_level(logging.WARNING, logger="secureai.worker"):
        assert run(["--poll-seconds", "0"]) == 2
    assert polls["n"] == 3
    assert shutdown_drain_seconds() == 75
    warnings = [
        record
        for record in caplog.records
        if record.levelno == logging.WARNING and "drain budget may be short" in record.getMessage()
    ]
    assert len(warnings) == 1
    message = warnings[0].getMessage()
    assert warnings[0].name == "secureai.worker"
    assert "DETECTOR_TIMEOUT_SECONDS=90" in message
    assert "drainingSeconds=75" in message
    assert "Raise drainingSeconds by 30" in message


def test_worker_railway_drain_matches_the_budget_and_has_no_healthcheck() -> None:
    payload = json.loads((REPO_ROOT / "deploy/railway/worker.railway.json").read_text())
    deploy = payload["deploy"]
    assert deploy["drainingSeconds"] == shutdown_drain_seconds()
    assert "healthcheckPath" not in deploy
    assert "healthcheckTimeout" not in deploy


def test_dockerfile_runs_the_worker_as_pid1() -> None:
    text = (WORKER_ROOT / "Dockerfile").read_text()
    cmd = next(line for line in text.splitlines() if line.startswith("CMD "))
    assert cmd == 'CMD ["python", "-m", "worker"]'
    assert "sh -c" not in text
    assert "HEALTHCHECK" not in text


def test_sigterm_finishes_the_popped_job_and_leaves_the_next(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("QUEUE_BACKEND", "memory")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    store = MemoryJobStore()
    queue = MemoryJobQueue()
    storage = FileSystemStorage(tmp_path)
    jobs = []
    for name in ("a.mp4", "b.mp4"):
        key = new_object_key("user_dev", name)
        storage.put(key, b"clip-bytes", "video/mp4")
        job = store.create(
            user_id="user_dev",
            filename=name,
            content_type="video/mp4",
            byte_size=len(b"clip-bytes"),
            object_key=key,
        )
        queue.publish(job.id)
        jobs.append(job)
    monkeypatch.setattr("worker.__main__.PostgresJobStore", lambda url: store)
    monkeypatch.setattr("worker.__main__.build_queue", lambda settings: queue)
    monkeypatch.setattr("worker.__main__.build_storage", lambda settings: storage)

    seen: list[str] = []

    def finish(job_store: MemoryJobStore, _storage: object, job_id: str, **_kwargs: object):
        seen.append(job_id)
        if len(seen) == 1:
            os.kill(os.getpid(), signal.SIGTERM)
        else:
            raise RuntimeError("took another job after SIGTERM")
        claimed = job_store.claim(job_id)
        assert claimed is not None
        return job_store.complete(
            job_id,
            prediction="real",
            confidence=0.5,
            attempt=claimed.attempt,
        )

    monkeypatch.setattr("worker.__main__.process_job", finish)
    previous_term = signal.getsignal(signal.SIGTERM)
    previous_int = signal.getsignal(signal.SIGINT)
    leaked: list[int] = []

    def swallow(signum: int, _frame: object) -> None:
        leaked.append(signum)

    signal.signal(signal.SIGTERM, swallow)
    try:
        assert run([], install_signal_handlers=True) == 0
        assert _live_webhook_threads() == []
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGINT, previous_int)
        for thread in _live_webhook_threads():
            thread.join(timeout=2)

    assert leaked == []
    assert seen == [jobs[0].id]
    finished = store.get_any(jobs[0].id)
    assert finished is not None
    assert finished.status is JobStatus.completed
    waiting = store.get_any(jobs[1].id)
    assert waiting is not None
    assert waiting.status is JobStatus.queued
    assert queue.consume() == jobs[1].id


class _WaitingQueue(MemoryJobQueue):
    """BRPOP stand-in. MemoryJobQueue.consume returns immediately and ignores timeout."""

    def __init__(self) -> None:
        super().__init__()
        self.waits = 0

    def consume(self, timeout: float = 0) -> str | None:
        self.waits += 1
        if self.waits > 40:
            raise RuntimeError("webhook shutdown did not stop the poll")
        if timeout > 0:
            time.sleep(timeout)
        return None


def _arm_webhook_worker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    queue: MemoryJobQueue,
) -> tuple[MemoryWebhookStore, MemoryWebhookQueue]:
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("QUEUE_BACKEND", "memory")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    webhooks = MemoryWebhookStore()
    webhook_queue = MemoryWebhookQueue()
    monkeypatch.setattr("worker.__main__.PostgresJobStore", lambda url: MemoryJobStore())
    monkeypatch.setattr("worker.__main__.build_queue", lambda settings: queue)
    monkeypatch.setattr(
        "worker.__main__.build_storage",
        lambda settings: FileSystemStorage(tmp_path),
    )
    monkeypatch.setattr("worker.__main__.open_webhook_store", lambda job_store: webhooks)
    monkeypatch.setattr("worker.__main__.build_webhook_queue", lambda settings: webhook_queue)
    return webhooks, webhook_queue


def _seed_deliveries(webhooks: MemoryWebhookStore, webhook_queue: MemoryWebhookQueue) -> tuple[str, str]:
    when = datetime(2026, 11, 1, tzinfo=timezone.utc)
    org_id = "org_abcdef012345"
    webhooks.upsert_endpoint(
        org_id=org_id,
        url="https://hooks.example/secureai",
        secret=None,
        keep_secret=False,
        notify_failures=True,
    )
    ids: list[str] = []
    for job_id in ("job_one", "job_two"):
        delivery = webhooks.create_delivery(
            org_id=org_id,
            job_id=job_id,
            payload='{"job_id":"%s"}' % job_id,
            now=when,
        )
        assert delivery is not None
        webhook_queue.publish(delivery.id, available_at=when.timestamp())
        ids.append(delivery.id)
    return ids[0], ids[1]


def test_sigterm_records_the_inflight_webhook_and_leaves_the_next_queued(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    queue = _WaitingQueue()
    webhooks, webhook_queue = _arm_webhook_worker(monkeypatch, tmp_path, queue)
    first_id, second_id = _seed_deliveries(webhooks, webhook_queue)
    release = threading.Event()
    calls: list[bytes] = []
    original_signal = signal.signal

    def post(url: str, body: bytes, headers: object, timeout: float) -> int:
        del url, headers, timeout
        calls.append(bytes(body))
        os.kill(os.getpid(), signal.SIGTERM)
        # Return only after the handler has set the stop flag, so a second
        # claim cannot sneak in between the signal and deliver_once returning.
        release.wait(timeout=3)
        return 204

    def capture(signum: int, handler: object):
        def wrapped(num: int, frame: object) -> None:
            handler(num, frame)  # type: ignore[operator]
            release.set()

        return original_signal(signum, wrapped)

    monkeypatch.setattr("worker.__main__.post_webhook", post)
    monkeypatch.setattr(signal, "signal", capture)
    previous_term = signal.getsignal(signal.SIGTERM)
    previous_int = signal.getsignal(signal.SIGINT)
    try:
        with caplog.at_level(logging.WARNING, logger="secureai.worker"):
            assert run(["--poll-seconds", "0.05"], install_signal_handlers=True) == 0
        assert _live_webhook_threads() == []
    finally:
        original_signal(signal.SIGTERM, previous_term)
        original_signal(signal.SIGINT, previous_int)
        release.set()
        for thread in _live_webhook_threads():
            thread.join(timeout=2)

    assert calls == [b'{"job_id":"job_one"}'] or calls == [b'{"job_id":"job_two"}']
    assert len(calls) == 1
    saved = [webhooks.get_delivery(first_id), webhooks.get_delivery(second_id)]
    succeeded = [row for row in saved if row is not None and row.status == "succeeded"]
    pending = [row for row in saved if row is not None and row.status == "pending"]
    assert len(succeeded) == 1
    assert len(pending) == 1
    assert succeeded[0].attempt == 1
    assert succeeded[0].last_status_code == 204
    assert succeeded[0].claim_token is None
    assert pending[0].attempt == 0
    assert pending[0].claim_token is None
    assert pending[0].delivering_until is None
    assert webhook_queue.claim(now=time.time()) == pending[0].id
    assert not any(
        "did not finish within" in record.getMessage()
        for record in caplog.records
        if record.levelno >= logging.WARNING
    )


def test_shutdown_join_limit_leaves_the_claim_leased(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    queue = _WaitingQueue()
    webhooks, webhook_queue = _arm_webhook_worker(monkeypatch, tmp_path, queue)
    first_id, second_id = _seed_deliveries(webhooks, webhook_queue)
    hold = threading.Event()
    monkeypatch.setattr(
        "worker.__main__.webhook_shutdown_join_seconds",
        lambda timeout_seconds: 0.2,
    )

    def post(url: str, body: bytes, headers: object, timeout: float) -> int:
        del url, body, headers, timeout
        os.kill(os.getpid(), signal.SIGTERM)
        hold.wait(timeout=2)
        return 204

    monkeypatch.setattr("worker.__main__.post_webhook", post)
    previous_term = signal.getsignal(signal.SIGTERM)
    previous_int = signal.getsignal(signal.SIGINT)
    signal.signal(signal.SIGTERM, lambda _signum, _frame: None)
    try:
        with caplog.at_level(logging.WARNING, logger="secureai.worker"):
            assert run(["--poll-seconds", "0.05"], install_signal_handlers=True) == 0
        claimed = [
            row
            for row in (webhooks.get_delivery(first_id), webhooks.get_delivery(second_id))
            if row is not None and row.claim_token
        ]
        waiting = [
            row
            for row in (webhooks.get_delivery(first_id), webhooks.get_delivery(second_id))
            if row is not None and row.claim_token is None
        ]
        assert len(claimed) == 1
        assert len(waiting) == 1
        assert claimed[0].status == "pending"
        assert claimed[0].attempt == 0
        assert waiting[0].status == "pending"
        assert waiting[0].attempt == 0
        assert webhook_queue.claim(now=time.time()) == waiting[0].id
        warnings = [
            record.getMessage()
            for record in caplog.records
            if record.levelno == logging.WARNING and record.name == "secureai.worker"
        ]
        assert any("did not finish within 0.2s of shutdown" in message for message in warnings)
        assert any("claim lease is the retry" in message for message in warnings)
    finally:
        hold.set()
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGINT, previous_int)
        for thread in _live_webhook_threads():
            thread.join(timeout=2)


def test_job_abort_stops_the_webhook_thread(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("QUEUE_BACKEND", "memory")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    store = MemoryJobStore()
    queue = MemoryJobQueue()
    storage = FileSystemStorage(tmp_path)
    key = new_object_key("user_dev", "clip.mp4")
    storage.put(key, b"clip-bytes", "video/mp4")
    job = store.create(
        user_id="user_dev",
        filename="clip.mp4",
        content_type="video/mp4",
        byte_size=len(b"clip-bytes"),
        object_key=key,
    )
    queue.publish(job.id)
    monkeypatch.setattr("worker.__main__.PostgresJobStore", lambda url: store)
    monkeypatch.setattr("worker.__main__.build_queue", lambda settings: queue)
    monkeypatch.setattr("worker.__main__.build_storage", lambda settings: storage)

    def boom(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("db down")

    monkeypatch.setattr("worker.__main__.process_job", boom)
    try:
        assert run(["--poll-seconds", "0.05"]) == 2
        assert _live_webhook_threads() == []
    finally:
        for thread in _live_webhook_threads():
            thread.join(timeout=2)
