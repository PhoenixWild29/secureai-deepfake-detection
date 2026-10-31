import pytest

from secureai_shared.models import JobStatus
from secureai_shared.queue import MemoryJobQueue, build_queue


def test_enqueue_and_get_round_trip() -> None:
    queue = MemoryJobQueue()
    created = queue.enqueue(filename="clip.mp4", content_type="video/mp4", byte_size=12)
    assert created.id.startswith("job_")
    assert created.status is JobStatus.queued
    assert queue.get(created.id) == created


def test_memory_queues_do_not_share_jobs() -> None:
    first = MemoryJobQueue()
    second = MemoryJobQueue()
    created = first.enqueue(filename="a.mp4", content_type=None, byte_size=None)
    assert second.get(created.id) is None


def test_claim_next_skips_non_queued_jobs() -> None:
    queue = MemoryJobQueue()
    first = queue.enqueue(filename="a.mp4", content_type=None, byte_size=1)
    second = queue.enqueue(filename="b.mp4", content_type=None, byte_size=2)
    claimed = queue.claim_next()
    assert claimed is not None
    assert claimed.id == first.id
    assert claimed.status is JobStatus.processing
    again = queue.claim_next()
    assert again is not None
    assert again.id == second.id
    assert queue.claim_next() is None


def test_redis_backend_is_not_implemented(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QUEUE_BACKEND", "redis")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    with pytest.raises(NotImplementedError):
        build_queue()


def test_default_backend_is_memory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QUEUE_BACKEND", raising=False)
    queue = build_queue()
    assert isinstance(queue, MemoryJobQueue)
