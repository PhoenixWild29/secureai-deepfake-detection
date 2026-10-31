"""Job persistence. Postgres is the product store. Memory is for unit tests."""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from secureai_shared.db import JobRow
from secureai_shared.models import JobRecord, JobStatus

# Client-visible failure text. Never store exception messages or paths here.
PUBLIC_FAILURE_DETAIL = "Detection failed."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return f"job_{uuid4().hex[:12]}"


def _record_from_row(row: JobRow) -> JobRecord:
    return JobRecord(
        id=row.id,
        user_id=row.user_id,
        filename=row.filename,
        content_type=row.content_type,
        byte_size=row.byte_size,
        object_key=row.object_key,
        status=JobStatus(row.status),
        prediction=row.prediction,
        confidence=row.confidence,
        detail=row.detail,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class JobStore(Protocol):
    def create(
        self,
        *,
        user_id: str,
        filename: str,
        content_type: str | None,
        byte_size: int | None,
        object_key: str,
    ) -> JobRecord: ...

    def get(self, job_id: str, *, user_id: str) -> JobRecord | None: ...

    def claim(self, job_id: str) -> JobRecord | None: ...

    def complete(self, job_id: str, *, prediction: str, confidence: float) -> JobRecord | None: ...

    def fail(self, job_id: str) -> JobRecord | None: ...


class MemoryJobStore:
    def __init__(self) -> None:
        self._rows: dict[str, JobRecord] = {}
        self._lock = threading.Lock()

    def create(
        self,
        *,
        user_id: str,
        filename: str,
        content_type: str | None,
        byte_size: int | None,
        object_key: str,
    ) -> JobRecord:
        now = _now()
        job = JobRecord(
            id=_new_id(),
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            byte_size=byte_size,
            object_key=object_key,
            status=JobStatus.queued,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._rows[job.id] = job
        return job

    def get(self, job_id: str, *, user_id: str) -> JobRecord | None:
        with self._lock:
            job = self._rows.get(job_id)
        if job is None or job.user_id != user_id:
            return None
        return job

    def claim(self, job_id: str) -> JobRecord | None:
        with self._lock:
            job = self._rows.get(job_id)
            if job is None or job.status is not JobStatus.queued:
                return None
            claimed = job.model_copy(
                update={"status": JobStatus.processing, "updated_at": _now()}
            )
            self._rows[job_id] = claimed
            return claimed

    def complete(self, job_id: str, *, prediction: str, confidence: float) -> JobRecord | None:
        return self._finish(
            job_id,
            status=JobStatus.completed,
            prediction=prediction,
            confidence=confidence,
            detail=None,
        )

    def fail(self, job_id: str) -> JobRecord | None:
        return self._finish(
            job_id,
            status=JobStatus.failed,
            prediction=None,
            confidence=None,
            detail=PUBLIC_FAILURE_DETAIL,
        )

    def _finish(
        self,
        job_id: str,
        *,
        status: JobStatus,
        prediction: str | None,
        confidence: float | None,
        detail: str | None,
    ) -> JobRecord | None:
        with self._lock:
            job = self._rows.get(job_id)
            if job is None:
                return None
            finished = job.model_copy(
                update={
                    "status": status,
                    "prediction": prediction,
                    "confidence": confidence,
                    "detail": detail,
                    "updated_at": _now(),
                }
            )
            self._rows[job_id] = finished
            return finished


class PostgresJobStore:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self._session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def create(
        self,
        *,
        user_id: str,
        filename: str,
        content_type: str | None,
        byte_size: int | None,
        object_key: str,
    ) -> JobRecord:
        now = _now()
        row = JobRow(
            id=_new_id(),
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            byte_size=byte_size,
            object_key=object_key,
            status=JobStatus.queued.value,
            prediction=None,
            confidence=None,
            detail=None,
            created_at=now,
            updated_at=now,
        )
        with self._session() as session:
            session.add(row)
            session.commit()
            return _record_from_row(row)

    def get(self, job_id: str, *, user_id: str) -> JobRecord | None:
        with self._session() as session:
            row = session.get(JobRow, job_id)
            if row is None or row.user_id != user_id:
                return None
            return _record_from_row(row)

    def claim(self, job_id: str) -> JobRecord | None:
        with self._session() as session:
            row = session.scalar(
                select(JobRow).where(JobRow.id == job_id).with_for_update()
            )
            if row is None or row.status != JobStatus.queued.value:
                return None
            row.status = JobStatus.processing.value
            row.updated_at = _now()
            session.commit()
            return _record_from_row(row)

    def complete(self, job_id: str, *, prediction: str, confidence: float) -> JobRecord | None:
        return self._finish(
            job_id,
            status=JobStatus.completed.value,
            prediction=prediction,
            confidence=confidence,
            detail=None,
        )

    def fail(self, job_id: str) -> JobRecord | None:
        return self._finish(
            job_id,
            status=JobStatus.failed.value,
            prediction=None,
            confidence=None,
            detail=PUBLIC_FAILURE_DETAIL,
        )

    def _finish(
        self,
        job_id: str,
        *,
        status: str,
        prediction: str | None,
        confidence: float | None,
        detail: str | None,
    ) -> JobRecord | None:
        with self._session() as session:
            row = session.get(JobRow, job_id)
            if row is None:
                return None
            row.status = status
            row.prediction = prediction
            row.confidence = confidence
            row.detail = detail
            row.updated_at = _now()
            session.commit()
            return _record_from_row(row)

    def _session(self) -> Session:
        return self._session_factory()
