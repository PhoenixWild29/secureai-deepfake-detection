"""Claim one queued job, score its object, and write the row back.

Client-visible failures use a fixed message. The exception stays in the log.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from detector import detect_video
from secureai_shared.models import JobRecord
from secureai_shared.storage import FileSystemStorage, ObjectStat, S3Storage
from secureai_shared.store import JobStore
from worker.detect_limit import DetectionTimeout, call_detect

logger = logging.getLogger("secureai.worker")

Detect = Callable[[str], dict[str, object]]


def process_job(
    store: JobStore,
    storage: FileSystemStorage | S3Storage,
    job_id: str,
    *,
    detect: Detect = detect_video,
    timeout_seconds: float = 60.0,
    max_upload_bytes: int = 50_000_000,
) -> JobRecord | None:
    job = store.claim(job_id)
    if job is None:
        logger.info("skip job_id=%s", job_id)
        return None

    media = None
    finished: JobRecord | None = None
    try:
        stat = storage.object_stat(job.object_key)
        if not _object_ok(stat, job, max_upload_bytes):
            logger.error("object rejected job_id=%s", job_id)
            finished = store.fail(job_id, attempt=job.attempt)
        else:
            media = storage.materialize(job.object_key)
            result = call_detect(
                detect,
                str(media.path),
                timeout_seconds,
                isolate=detect is detect_video,
            )
            prediction = result["prediction"]
            confidence = float(result["confidence"])  # type: ignore[arg-type]
            if prediction not in {"real", "fake"}:
                raise ValueError("unexpected prediction")
            if not 0.0 <= confidence <= 1.0:
                raise ValueError("unexpected confidence")
            finished = store.complete(
                job_id,
                prediction=str(prediction),
                confidence=confidence,
                attempt=job.attempt,
            )
    except DetectionTimeout:
        logger.error("detector timed out job_id=%s", job_id)
        finished = store.fail(job_id, attempt=job.attempt)
    except Exception:
        logger.exception("job failed job_id=%s", job_id)
        finished = store.fail(job_id, attempt=job.attempt)
    finally:
        if media is not None and media.cleanup:
            media.path.unlink(missing_ok=True)

    if finished is None:
        return None
    logger.info(
        "finished job_id=%s status=%s prediction=%s",
        finished.id,
        finished.status.value,
        finished.prediction,
    )
    return finished


def _object_ok(stat: ObjectStat | None, job: JobRecord, max_upload_bytes: int) -> bool:
    """Reject a missing, oversized, or rewritten object before opening it."""

    if stat is None or stat.size < 1 or stat.size > max_upload_bytes:
        return False
    if job.byte_size is not None and stat.size != job.byte_size:
        return False
    if job.object_etag and stat.etag != job.object_etag:
        return False
    return True
