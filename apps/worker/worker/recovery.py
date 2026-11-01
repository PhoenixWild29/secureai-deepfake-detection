"""Return abandoned in-flight jobs to the queue, or fail them after repeated crashes."""

from __future__ import annotations

import logging

from secureai_shared.models import JobStatus
from secureai_shared.queue import JobQueue
from secureai_shared.store import JobStore

logger = logging.getLogger("secureai.worker")


def sweep_stuck(
    store: JobStore,
    queue: JobQueue,
    *,
    lease_seconds: float,
    max_attempts: int,
    now: float | None = None,
) -> list[str]:
    """Requeue leased jobs that outlived the detector timeout, or fail them.

    `claim_stale` refreshes the lease and republishes the id in one step, and
    only if the attempt this sweep observed is still the stored attempt. It
    bumps the lease generation and leaves the attempt count unchanged, so the
    worker that popped the old generation cannot ack the new lease or reset
    the attempt counter. `release` is attempt-aware, so a slow worker cannot
    move a newer claim back to queued. The database release commits before
    the republish, so a worker that pops the id can claim the row.
    """

    recovered: list[str] = []
    for job_id, attempts in queue.stale(lease_seconds, now=now):
        job = store.get_any(job_id)
        if job is None or job.status in {JobStatus.completed, JobStatus.failed}:
            queue.ack(job_id, attempt=attempts)
            continue
        if attempts >= max_attempts:
            if job.status is JobStatus.processing:
                failed = store.fail(job_id, attempt=job.attempt)
            else:
                failed = store.fail(job_id)
            if failed is not None and queue.ack(job_id, attempt=attempts):
                logger.error("stuck job failed job_id=%s attempts=%s", job_id, attempts)
                recovered.append(job_id)
            continue
        if job.status is JobStatus.processing:
            if not store.release(job_id, attempt=job.attempt):
                continue
        if not queue.claim_stale(job_id, attempts, now=now, lease_seconds=lease_seconds):
            continue
        logger.info("stuck job requeued job_id=%s attempts=%s", job_id, attempts)
        recovered.append(job_id)
    return recovered


def rescue_popped(store: JobStore, queue: JobQueue, job_id: str) -> None:
    """Put a popped id back, or mark the row failed, before the worker exits.

    Called when claim or fail raises. A successful terminal write acks the
    lease. A queued row is published again. A processing row we still own is
    failed, or released and published when the database rejects the failure.
    Lease writes carry the attempt from this pop, so they do not clear a
    newer claim.
    """

    lease_attempt = queue.held_attempt(job_id)
    try:
        job = store.get_any(job_id)
    except Exception:
        logger.exception("status unread job_id=%s", job_id)
        if queue.renew(job_id, attempt=lease_attempt):
            queue.publish(job_id)
        return
    if job is None or job.status in {JobStatus.completed, JobStatus.failed}:
        queue.ack(job_id, attempt=lease_attempt)
        return
    if job.status is JobStatus.processing:
        try:
            failed = store.fail(job_id, attempt=job.attempt)
        except Exception:
            logger.exception("fail during rescue job_id=%s", job_id)
            try:
                released = store.release(job_id, attempt=job.attempt)
            except Exception:
                logger.exception("release during rescue job_id=%s", job_id)
                released = False
            if released and queue.renew(job_id, attempt=lease_attempt):
                queue.publish(job_id)
            return
        if failed is not None:
            queue.ack(job_id, attempt=lease_attempt)
            return
        return
    if queue.renew(job_id, attempt=lease_attempt):
        queue.publish(job_id)
