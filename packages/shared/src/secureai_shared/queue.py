"""Phase 0 job queue.

The product design requires Redis. This module does not connect to it.

TODO(phase-1): add a RedisJobQueue that BRPOPs a list and stores the job row
in Postgres. API and worker processes must share that queue. Delete the
process-local MemoryJobQueue from the default path once Redis is required.
"""

from __future__ import annotations

import os
import threading
from typing import Protocol
from uuid import uuid4

from secureai_shared.models import JobRecord, JobStatus


class JobQueue(Protocol):
    def enqueue(
        self,
        *,
        filename: str,
        content_type: str | None,
        byte_size: int | None,
    ) -> JobRecord: ...

    def get(self, job_id: str) -> JobRecord | None: ...

    def claim_next(self) -> JobRecord | None: ...

    def save(self, job: JobRecord) -> JobRecord: ...


class MemoryJobQueue:
    """Process-local queue. A second process cannot see these jobs."""

    def __init__(self) -> None:
        self._jobs: dict[str, JobRecord] = {}
        self._order: list[str] = []
        self._lock = threading.Lock()

    def enqueue(
        self,
        *,
        filename: str,
        content_type: str | None,
        byte_size: int | None,
    ) -> JobRecord:
        job = JobRecord(
            id=f"job_{uuid4().hex[:12]}",
            filename=filename,
            content_type=content_type,
            byte_size=byte_size,
            status=JobStatus.queued,
        )
        with self._lock:
            self._jobs[job.id] = job
            self._order.append(job.id)
        return job

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._jobs.get(job_id)

    def claim_next(self) -> JobRecord | None:
        with self._lock:
            for job_id in self._order:
                current = self._jobs[job_id]
                if current.status is not JobStatus.queued:
                    continue
                claimed = current.model_copy(update={"status": JobStatus.processing})
                self._jobs[job_id] = claimed
                return claimed
        return None

    def save(self, job: JobRecord) -> JobRecord:
        with self._lock:
            if job.id not in self._jobs:
                raise KeyError(job.id)
            self._jobs[job.id] = job
        return job


class RedisJobQueue:
    """Placeholder. Constructing it is an error until Phase 1."""

    def __init__(self, url: str) -> None:
        self.url = url
        raise NotImplementedError(
            "QUEUE_BACKEND=redis is not implemented. Phase 1 will connect "
            "Redis and Postgres. Use QUEUE_BACKEND=memory for the Phase 0 stub."
        )


def build_queue() -> JobQueue:
    """Build the queue selected by QUEUE_BACKEND.

    Unset or `memory` returns a new MemoryJobQueue. `redis` raises
    NotImplementedError even if REDIS_URL is present, so a stray secret
    cannot silently change Phase 0 behavior.
    """

    backend = os.environ.get("QUEUE_BACKEND", "memory").strip().lower()
    if backend in {"", "memory"}:
        return MemoryJobQueue()
    if backend == "redis":
        return RedisJobQueue(os.environ.get("REDIS_URL", ""))
    raise ValueError(
        f"Unsupported QUEUE_BACKEND={backend!r}. Phase 0 supports 'memory' only."
    )
