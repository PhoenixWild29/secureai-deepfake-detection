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
    """Requeue leased jobs that outlived the detector timeout, or fail them."""

    recovered: list[str] = []
    for job_id, attempts in queue.stale(lease_seconds, now=now):
        job = store.get_any(job_id)
        if job is None or job.status in {JobStatus.completed, JobStatus.failed}:
            queue.ack(job_id)
            continue
        if attempts >= max_attempts:
            failed = store.fail(job_id)
            queue.ack(job_id)
            logger.error("stuck job failed job_id=%s attempts=%s", job_id, attempts)
            if failed is not None:
                recovered.append(job_id)
            continue
        if job.status is JobStatus.processing:
            store.release(job_id)
        queue.renew(job_id, now=now)
        queue.publish(job_id)
        logger.info("stuck job requeued job_id=%s attempts=%s", job_id, attempts)
        recovered.append(job_id)
    return recovered


def rescue_popped(store: JobStore, queue: JobQueue, job_id: str) -> None:
    """Put a popped id back, or mark the row failed, before the worker exits.

    Called when claim or fail raises. A successful terminal write acks the
    lease. A queued row is published again. A processing row we still own is
    failed, or released and published when the database rejects the failure.
    """

    try:
        job = store.get_any(job_id)
    except Exception:
        logger.exception("status unread job_id=%s", job_id)
        queue.publish(job_id)
        queue.renew(job_id)
        return
    if job is None or job.status in {JobStatus.completed, JobStatus.failed}:
        queue.ack(job_id)
        return
    if job.status is JobStatus.processing:
        try:
            failed = store.fail(job_id, attempt=job.attempt)
        except Exception:
            logger.exception("fail during rescue job_id=%s", job_id)
            try:
                store.release(job_id)
            except Exception:
                logger.exception("release during rescue job_id=%s", job_id)
            queue.publish(job_id)
            queue.renew(job_id)
            return
        if failed is not None:
            queue.ack(job_id)
            return
        return
    queue.publish(job_id)
    queue.renew(job_id)
