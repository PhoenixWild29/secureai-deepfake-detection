import logging

import pytest

from secureai_shared.models import JobStatus
from secureai_shared.queue import MemoryJobQueue
from worker.consumer import process_next
from worker.__main__ import run


def test_process_next_completes_with_detector_stub() -> None:
    queue = MemoryJobQueue()
    created = queue.enqueue(filename="clip.mp4", content_type="video/mp4", byte_size=3)
    finished = process_next(queue)
    assert finished is not None
    assert finished.id == created.id
    assert finished.status is JobStatus.completed
    assert finished.prediction in {"real", "fake"}
    assert finished.confidence is not None
    assert 0.5 <= finished.confidence <= 0.99
    assert queue.get(created.id) == finished


def test_process_next_on_empty_queue() -> None:
    assert process_next(MemoryJobQueue()) is None


def test_demo_once_exits_clean(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    assert run(["--demo", "--once"]) == 0
    assert any("completed job_id=" in record.message for record in caplog.records)


def test_redis_backend_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUEUE_BACKEND", "redis")
    assert run(["--once"]) == 2
