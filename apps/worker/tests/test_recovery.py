from secureai_shared.models import JobStatus
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.storage import new_object_key
from secureai_shared.store import PUBLIC_FAILURE_DETAIL, MemoryJobStore
from worker.recovery import rescue_popped, sweep_stuck


def _queued() -> tuple[MemoryJobStore, MemoryJobQueue, str]:
    store = MemoryJobStore()
    queue = MemoryJobQueue()
    job = store.create(
        user_id="user_dev",
        filename="clip.mp4",
        content_type="video/mp4",
        byte_size=4,
        object_key=new_object_key("user_dev", "clip.mp4"),
    )
    queue.publish(job.id)
    return store, queue, job.id


def test_sweep_requeues_a_processing_job_inside_the_attempt_budget() -> None:
    store, queue, job_id = _queued()
    assert queue.consume() == job_id
    assert store.claim(job_id) is not None
    queue._inflight[job_id] = (1_000.0, 1)  # noqa: SLF001
    recovered = sweep_stuck(store, queue, lease_seconds=10, max_attempts=3, now=2_000)
    assert recovered == [job_id]
    job = store.get_any(job_id)
    assert job is not None
    assert job.status is JobStatus.queued
    assert queue.consume() == job_id


def test_sweep_does_not_duplicate_a_requeue_that_is_still_waiting() -> None:
    store, queue, job_id = _queued()
    assert queue.consume() == job_id
    assert store.claim(job_id) is not None
    queue._inflight[job_id] = (1_000.0, 1)  # noqa: SLF001
    assert sweep_stuck(store, queue, lease_seconds=10, max_attempts=3, now=2_000) == [job_id]
    job = store.get_any(job_id)
    assert job is not None
    assert job.status is JobStatus.queued
    queue.publish(job_id)
    assert sweep_stuck(store, queue, lease_seconds=10, max_attempts=3, now=3_000) == []
    assert queue.consume() == job_id
    assert queue.held_attempt(job_id) == 2
    assert queue.consume() is None
    claimed = store.claim(job_id)
    assert claimed is not None
    assert claimed.attempt == 2
    assert queue.ack(job_id, attempt=1) is False
    assert queue.ack(job_id, attempt=2) is True


def test_sweep_fails_a_job_that_exhausted_attempts() -> None:
    store, queue, job_id = _queued()
    assert queue.consume() == job_id
    assert store.claim(job_id) is not None
    queue._inflight[job_id] = (0.0, 3)  # noqa: SLF001
    recovered = sweep_stuck(store, queue, lease_seconds=10, max_attempts=3, now=1_000)
    assert recovered == [job_id]
    job = store.get_any(job_id)
    assert job is not None
    assert job.status is JobStatus.failed
    assert job.detail == PUBLIC_FAILURE_DETAIL
    assert job_id not in queue._inflight  # noqa: SLF001


def test_release_ignores_a_stale_attempt() -> None:
    store, _queue, job_id = _queued()
    claimed = store.claim(job_id)
    assert claimed is not None
    assert store.release(job_id, attempt=claimed.attempt) is True
    again = store.claim(job_id)
    assert again is not None
    assert store.release(job_id, attempt=claimed.attempt) is False
    job = store.get_any(job_id)
    assert job is not None
    assert job.status is JobStatus.processing
    assert job.attempt == again.attempt
    assert store.release(job_id, attempt=again.attempt) is True


def test_slow_worker_cannot_fail_a_reclaimed_job() -> None:
    store, queue, job_id = _queued()
    assert queue.consume() == job_id
    first = store.claim(job_id)
    assert first is not None
    queue._inflight[job_id] = (0.0, 1)  # noqa: SLF001
    assert sweep_stuck(store, queue, lease_seconds=10, max_attempts=3, now=1_000) == [job_id]
    second = store.claim(job_id)
    assert second is not None
    assert store.fail(job_id, attempt=first.attempt) is None
    job = store.get_any(job_id)
    assert job is not None
    assert job.status is JobStatus.processing
    assert job.attempt == second.attempt


def test_sweep_notifies_a_terminal_job_and_not_a_requeue() -> None:
    store, queue, job_id = _queued()
    assert queue.consume() == job_id
    assert store.claim(job_id) is not None
    queue._inflight[job_id] = (1_000.0, 1)  # noqa: SLF001
    requeued: list[str] = []
    sweep_stuck(
        store,
        queue,
        lease_seconds=10,
        max_attempts=3,
        now=2_000,
        on_terminal=lambda job: requeued.append(job.status.value),
    )
    assert requeued == []

    assert queue.consume() == job_id
    queue._inflight[job_id] = (0.0, 3)  # noqa: SLF001
    failed: list[str] = []
    sweep_stuck(
        store,
        queue,
        lease_seconds=10,
        max_attempts=3,
        now=1_000,
        on_terminal=lambda job: failed.append(job.status.value),
    )
    assert failed == ["failed"]


def test_rescue_republishes_when_claim_never_landed() -> None:
    store, queue, job_id = _queued()
    assert queue.consume() == job_id
    rescue_popped(store, queue, job_id)
    assert store.get_any(job_id) is not None
    assert store.get_any(job_id).status is JobStatus.queued  # type: ignore[union-attr]
    assert queue.consume() == job_id


def test_rescue_requeues_when_fail_raises() -> None:
    store, queue, job_id = _queued()
    assert queue.consume() == job_id
    assert store.claim(job_id) is not None

    def explode(job_id: str, *, attempt: int | None = None):  # noqa: ARG001
        raise RuntimeError("db down")

    store.fail = explode  # type: ignore[method-assign]
    rescue_popped(store, queue, job_id)
    job = store.get_any(job_id)
    assert job is not None
    assert job.status is JobStatus.queued
    assert queue.consume() == job_id
