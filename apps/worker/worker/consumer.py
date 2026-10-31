"""Claim one queued job, score its object, and write the row back.

Client-visible failures use a fixed message. The exception stays in the log.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from detector import detect_video
from secureai_shared.models import JobRecord
from secureai_shared.storage import FileSystemStorage, S3Storage
from secureai_shared.store import JobStore

logger = logging.getLogger("secureai.worker")

Detect = Callable[[str], dict[str, object]]


def process_job(
    store: JobStore,
    storage: FileSystemStorage | S3Storage,
    job_id: str,
    *,
    detect: Detect = detect_video,
) -> JobRecord | None:
    job = store.claim(job_id)
    if job is None:
        logger.info("skip job_id=%s", job_id)
        return None

    media = None
    try:
        media = storage.materialize(job.object_key)
        result = detect(str(media.path))
        prediction = result["prediction"]
        confidence = float(result["confidence"])  # type: ignore[arg-type]
        if prediction not in {"real", "fake"}:
            raise ValueError("unexpected prediction")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("unexpected confidence")
        finished = store.complete(job_id, prediction=str(prediction), confidence=confidence)
    except Exception:
        logger.exception("job failed job_id=%s", job_id)
        finished = store.fail(job_id)
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
