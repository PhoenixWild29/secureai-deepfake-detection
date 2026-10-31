"""Consume one job from a queue and score it with the detector stub.

The API enqueues the same JobRecord shape onto its own MemoryJobQueue.
Those two queues do not share memory. Phase 1 replaces both with Redis.
"""

import logging

from detector import detect_video
from secureai_shared.models import JobRecord, JobStatus
from secureai_shared.queue import JobQueue

logger = logging.getLogger("secureai.worker")


def process_next(queue: JobQueue) -> JobRecord | None:
    job = queue.claim_next()
    if job is None:
        return None
    try:
        # Phase 0 passes the filename token. Phase 1 passes a downloaded path.
        result = detect_video(job.filename)
        prediction = result["prediction"]
        confidence = float(result["confidence"])
        if prediction not in {"real", "fake"}:
            raise ValueError(f"unexpected prediction {prediction!r}")
        finished = job.model_copy(
            update={
                "status": JobStatus.completed,
                "prediction": prediction,
                "confidence": confidence,
                "detail": None,
            }
        )
    except Exception as exc:
        logger.exception("job failed job_id=%s", job.id)
        finished = job.model_copy(
            update={"status": JobStatus.failed, "detail": str(exc)}
        )
    queue.save(finished)
    logger.info(
        "completed job_id=%s status=%s prediction=%s confidence=%s",
        finished.id,
        finished.status.value,
        finished.prediction,
        finished.confidence,
    )
    return finished
