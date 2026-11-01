"""SIGTERM finishes the popped job, and the Railway drain covers that wait."""

from __future__ import annotations

import json
import math
import os
import signal
import threading
from inspect import signature
from pathlib import Path

import pytest

from secureai_shared.models import JobStatus
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.reporting import flush_error_reporting
from secureai_shared.settings import Settings
from secureai_shared.storage import FileSystemStorage, new_object_key
from secureai_shared.store import MemoryJobStore
from worker.__main__ import (
    DRAIN_MARGIN_SECONDS,
    DEFAULT_POLL_SECONDS,
    SENTRY_FLUSH_SECONDS,
    run,
    shutdown_drain_seconds,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKER_ROOT = Path(__file__).resolve().parents[1]


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
    finally:
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGINT, previous_int)
        for thread in threading.enumerate():
            if thread.name == "secureai-webhooks":
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
