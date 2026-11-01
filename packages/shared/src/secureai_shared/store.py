"""Job persistence. Postgres is the product store. Memory is for unit tests."""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol
from uuid import uuid4

from sqlalchemy import and_, create_engine, func, not_, select, text, tuple_
from sqlalchemy.orm import Session, sessionmaker

from secureai_shared.db import JobRow, JobTombstoneRow
from secureai_shared.models import JobRecord, JobStatus

# Client-visible failure text. Never store exception messages or paths here.
PUBLIC_FAILURE_DETAIL = "Detection failed."
# Publish failed before the id reached Redis. These rows do not spend quota.
UNQUEUED_FAILURE_DETAIL = "Could not queue the job."


class DiscardState(str, Enum):
    """Result of removing a job the caller can already see.

    ``busy`` means a worker holds the row in ``processing``. ``missing``
    means the row is already gone. ``removed`` means the row was deleted.
    """

    removed = "removed"
    busy = "busy"
    missing = "missing"


@dataclass(frozen=True)
class _QuotaTombstone:
    job_id: str
    user_id: str
    org_id: str | None
    created_at: datetime


def _visible(job: JobRecord | None, *, user_id: str, org_id: str | None) -> JobRecord | None:
    """Personal reads hide workspace jobs. Workspace reads require that workspace."""

    if job is None:
        return None
    if org_id is not None:
        if job.org_id != org_id:
            return None
        return job
    if job.user_id != user_id or job.org_id is not None:
        return None
    return job


def _can_finish(job: JobRecord, *, attempt: int | None, require_processing: bool) -> bool:
    if job.status in {JobStatus.completed, JobStatus.failed}:
        return False
    if require_processing and job.status is not JobStatus.processing:
        return False
    if attempt is not None and job.attempt != attempt:
        return False
    return True


def _counts_toward_quota(job: JobRecord) -> bool:
    return not (
        job.status is JobStatus.failed
        and job.attempt == 0
        and job.detail == UNQUEUED_FAILURE_DETAIL
    )


def _quota_clause():
    """SQL twin of `_counts_toward_quota`."""

    return not_(
        and_(
            JobRow.status == JobStatus.failed.value,
            JobRow.attempt == 0,
            JobRow.detail == UNQUEUED_FAILURE_DETAIL,
        )
    )


def _tombstone_count(
    session: Session,
    *,
    user_id: str,
    org_id: str | None,
    since: datetime,
) -> int:
    query = (
        select(func.count())
        .select_from(JobTombstoneRow)
        .where(JobTombstoneRow.created_at >= since)
    )
    if org_id is not None:
        query = query.where(JobTombstoneRow.org_id == org_id)
    else:
        query = query.where(
            JobTombstoneRow.user_id == user_id,
            JobTombstoneRow.org_id.is_(None),
        )
    return int(session.scalar(query) or 0)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _before_clause(created_at: datetime, job_id: str):
    """Rows strictly older than the keyset ``(created_at, job_id)``.

    Newest-first order is ``created_at DESC, id DESC``. ``id`` breaks ties so
    two rows written in one batch, which share a timestamp, stay on a stable
    page boundary. The predicate is one row comparison, which is the same as
    ``created_at < cursor OR (created_at = cursor AND id < cursor_id)`` when
    both columns are non-null. Postgres can seek that form on
    ``ix_jobs_personal_created_id`` and ``ix_jobs_org_created_id``. An ``OR``
    walks every newer row before the limit. ``id`` uses the column collation.
    Ids are ``job_`` plus lowercase hex, which sorts the same as the in-memory
    code-point order.
    """

    return tuple_(JobRow.created_at, JobRow.id) < tuple_(created_at, job_id)


def _page(
    rows: list[JobRecord],
    *,
    limit: int,
    before: tuple[datetime, str] | None,
) -> list[JobRecord]:
    """Newest first, then the next older page when ``before`` is set."""

    if before is not None:
        rows = [job for job in rows if (job.created_at, job.id) < before]
    rows.sort(key=lambda job: (job.created_at, job.id), reverse=True)
    return rows[:limit]


def _new_id() -> str:
    return f"job_{uuid4().hex[:12]}"


def _record_from_row(row: JobRow) -> JobRecord:
    return JobRecord(
        id=row.id,
        user_id=row.user_id,
        org_id=row.org_id,
        filename=row.filename,
        content_type=row.content_type,
        byte_size=row.byte_size,
        object_key=row.object_key,
        status=JobStatus(row.status),
        prediction=row.prediction,
        confidence=row.confidence,
        detail=row.detail,
        attempt=row.attempt,
        object_etag=row.object_etag,
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
        object_etag: str | None = None,
        org_id: str | None = None,
    ) -> JobRecord: ...

    def create_many(
        self,
        *,
        user_id: str,
        org_id: str | None,
        items: list[tuple[str, str | None, int | None, str, str | None]],
    ) -> list[JobRecord]:
        """Insert every item in one transaction. A failure leaves no new rows.

        Each item is ``(filename, content_type, byte_size, object_key, object_etag)``.
        """

    def get(self, job_id: str, *, user_id: str, org_id: str | None = None) -> JobRecord | None: ...

    def get_any(self, job_id: str) -> JobRecord | None: ...

    def list_for_user(
        self,
        user_id: str,
        *,
        limit: int = 50,
        before: tuple[datetime, str] | None = None,
    ) -> list[JobRecord]: ...

    def list_for_org(
        self,
        org_id: str,
        *,
        limit: int = 50,
        before: tuple[datetime, str] | None = None,
    ) -> list[JobRecord]: ...

    def count_started(
        self,
        *,
        user_id: str,
        org_id: str | None,
        since: datetime,
    ) -> int: ...

    def claim(self, job_id: str) -> JobRecord | None: ...

    def release(self, job_id: str, *, attempt: int | None = None) -> bool: ...

    def complete(
        self,
        job_id: str,
        *,
        prediction: str,
        confidence: float,
        attempt: int | None = None,
        detail: str | None = None,
    ) -> JobRecord | None: ...

    def fail(
        self,
        job_id: str,
        *,
        attempt: int | None = None,
        detail: str | None = None,
    ) -> JobRecord | None: ...

    def discard(self, job_id: str, *, delete_object: Callable[[str], None]) -> DiscardState:
        """Delete a job that is not processing, then erase its video when unused.

        ``delete_object`` runs only when no other job still references the
        object key, and it runs before the row is removed. A raise leaves
        the row in place. A job that counted toward the quota leaves a
        tombstone. A job that never reached the queue does not.
        """


class MemoryJobStore:
    def __init__(self) -> None:
        self._rows: dict[str, JobRecord] = {}
        self._tombstones: dict[str, _QuotaTombstone] = {}
        self._lock = threading.Lock()

    def create(
        self,
        *,
        user_id: str,
        filename: str,
        content_type: str | None,
        byte_size: int | None,
        object_key: str,
        object_etag: str | None = None,
        org_id: str | None = None,
    ) -> JobRecord:
        now = _now()
        job = JobRecord(
            id=_new_id(),
            user_id=user_id,
            org_id=org_id,
            filename=filename,
            content_type=content_type,
            byte_size=byte_size,
            object_key=object_key,
            object_etag=object_etag,
            status=JobStatus.queued,
            attempt=0,
            created_at=now,
            updated_at=now,
        )
        with self._lock:
            self._rows[job.id] = job
        return job

    def create_many(
        self,
        *,
        user_id: str,
        org_id: str | None,
        items: list[tuple[str, str | None, int | None, str, str | None]],
    ) -> list[JobRecord]:
        created: list[JobRecord] = []
        with self._lock:
            try:
                for filename, content_type, byte_size, object_key, object_etag in items:
                    now = _now()
                    job = JobRecord(
                        id=_new_id(),
                        user_id=user_id,
                        org_id=org_id,
                        filename=filename,
                        content_type=content_type,
                        byte_size=byte_size,
                        object_key=object_key,
                        object_etag=object_etag,
                        status=JobStatus.queued,
                        attempt=0,
                        created_at=now,
                        updated_at=now,
                    )
                    self._rows[job.id] = job
                    created.append(job)
            except Exception:
                for job in created:
                    self._rows.pop(job.id, None)
                raise
        return created

    def get(self, job_id: str, *, user_id: str, org_id: str | None = None) -> JobRecord | None:
        with self._lock:
            job = self._rows.get(job_id)
        return _visible(job, user_id=user_id, org_id=org_id)

    def get_any(self, job_id: str) -> JobRecord | None:
        with self._lock:
            return self._rows.get(job_id)

    def list_for_user(
        self,
        user_id: str,
        *,
        limit: int = 50,
        before: tuple[datetime, str] | None = None,
    ) -> list[JobRecord]:
        with self._lock:
            rows = [
                job for job in self._rows.values() if job.user_id == user_id and job.org_id is None
            ]
        return _page(rows, limit=limit, before=before)

    def list_for_org(
        self,
        org_id: str,
        *,
        limit: int = 50,
        before: tuple[datetime, str] | None = None,
    ) -> list[JobRecord]:
        with self._lock:
            rows = [job for job in self._rows.values() if job.org_id == org_id]
        return _page(rows, limit=limit, before=before)

    def count_started(self, *, user_id: str, org_id: str | None, since: datetime) -> int:
        with self._lock:
            rows = self._rows.values()
            if org_id is not None:
                matched = [job for job in rows if job.org_id == org_id and job.created_at >= since]
            else:
                matched = [
                    job
                    for job in rows
                    if job.user_id == user_id and job.org_id is None and job.created_at >= since
                ]
            tombs = [
                row
                for row in self._tombstones.values()
                if row.created_at >= since
                and (
                    (org_id is not None and row.org_id == org_id)
                    or (org_id is None and row.user_id == user_id and row.org_id is None)
                )
            ]
        return sum(1 for job in matched if _counts_toward_quota(job)) + len(tombs)

    def claim(self, job_id: str) -> JobRecord | None:
        with self._lock:
            job = self._rows.get(job_id)
            if job is None or job.status is not JobStatus.queued:
                return None
            claimed = job.model_copy(
                update={
                    "status": JobStatus.processing,
                    "attempt": job.attempt + 1,
                    "updated_at": _now(),
                }
            )
            self._rows[job_id] = claimed
            return claimed

    def release(self, job_id: str, *, attempt: int | None = None) -> bool:
        with self._lock:
            job = self._rows.get(job_id)
            if job is None or job.status is not JobStatus.processing:
                return False
            if attempt is not None and job.attempt != attempt:
                return False
            self._rows[job_id] = job.model_copy(
                update={"status": JobStatus.queued, "updated_at": _now()}
            )
            return True

    def complete(
        self,
        job_id: str,
        *,
        prediction: str,
        confidence: float,
        attempt: int | None = None,
        detail: str | None = None,
    ) -> JobRecord | None:
        return self._finish(
            job_id,
            status=JobStatus.completed,
            prediction=prediction,
            confidence=confidence,
            detail=detail,
            attempt=attempt,
            require_processing=True,
        )

    def fail(
        self,
        job_id: str,
        *,
        attempt: int | None = None,
        detail: str | None = None,
    ) -> JobRecord | None:
        # A worker passes the attempt it claimed. That must not fail a job
        # another worker has since re-queued or re-claimed.
        return self._finish(
            job_id,
            status=JobStatus.failed,
            prediction=None,
            confidence=None,
            detail=detail or PUBLIC_FAILURE_DETAIL,
            attempt=attempt,
            require_processing=attempt is not None,
        )

    def _finish(
        self,
        job_id: str,
        *,
        status: JobStatus,
        prediction: str | None,
        confidence: float | None,
        detail: str | None,
        attempt: int | None,
        require_processing: bool,
    ) -> JobRecord | None:
        with self._lock:
            job = self._rows.get(job_id)
            if job is None or not _can_finish(job, attempt=attempt, require_processing=require_processing):
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

    def discard(self, job_id: str, *, delete_object: Callable[[str], None]) -> DiscardState:
        with self._lock:
            job = self._rows.get(job_id)
            if job is None:
                return DiscardState.missing
            if job.status is JobStatus.processing:
                return DiscardState.busy
            key = job.object_key
            shared = any(
                other.id != job_id and other.object_key == key for other in self._rows.values()
            )
            # Raise before any mutation so a storage error keeps the job.
            if not shared:
                delete_object(key)
            if _counts_toward_quota(job):
                self._tombstones[job.id] = _QuotaTombstone(
                    job_id=job.id,
                    user_id=job.user_id,
                    org_id=job.org_id,
                    created_at=job.created_at,
                )
            del self._rows[job_id]
            return DiscardState.removed


class PostgresJobStore:
    def __init__(self, database_url: str) -> None:
        self.engine = create_engine(database_url, pool_pre_ping=True, hide_parameters=True)
        self._session_factory = sessionmaker(self.engine, expire_on_commit=False)

    def create(
        self,
        *,
        user_id: str,
        filename: str,
        content_type: str | None,
        byte_size: int | None,
        object_key: str,
        object_etag: str | None = None,
        org_id: str | None = None,
    ) -> JobRecord:
        now = _now()
        row = JobRow(
            id=_new_id(),
            user_id=user_id,
            org_id=org_id,
            filename=filename,
            content_type=content_type,
            byte_size=byte_size,
            object_key=object_key,
            object_etag=object_etag,
            status=JobStatus.queued.value,
            prediction=None,
            confidence=None,
            detail=None,
            attempt=0,
            created_at=now,
            updated_at=now,
        )
        with self._session() as session:
            session.add(row)
            session.commit()
            return _record_from_row(row)

    def create_many(
        self,
        *,
        user_id: str,
        org_id: str | None,
        items: list[tuple[str, str | None, int | None, str, str | None]],
    ) -> list[JobRecord]:
        now = _now()
        rows = [
            JobRow(
                id=_new_id(),
                user_id=user_id,
                org_id=org_id,
                filename=filename,
                content_type=content_type,
                byte_size=byte_size,
                object_key=object_key,
                object_etag=object_etag,
                status=JobStatus.queued.value,
                prediction=None,
                confidence=None,
                detail=None,
                attempt=0,
                created_at=now,
                updated_at=now,
            )
            for filename, content_type, byte_size, object_key, object_etag in items
        ]
        with self._session() as session:
            try:
                session.add_all(rows)
                session.commit()
            except Exception:
                # A failed flush leaves Postgres in an aborted transaction.
                # Roll the whole batch back before the error leaves this method.
                session.rollback()
                raise
            return [_record_from_row(row) for row in rows]

    def get(self, job_id: str, *, user_id: str, org_id: str | None = None) -> JobRecord | None:
        with self._session() as session:
            row = session.get(JobRow, job_id)
            visible = _visible(None if row is None else _record_from_row(row), user_id=user_id, org_id=org_id)
            return visible

    def get_any(self, job_id: str) -> JobRecord | None:
        with self._session() as session:
            row = session.get(JobRow, job_id)
            if row is None:
                return None
            return _record_from_row(row)

    def list_for_user(
        self,
        user_id: str,
        *,
        limit: int = 50,
        before: tuple[datetime, str] | None = None,
    ) -> list[JobRecord]:
        with self._session() as session:
            query = select(JobRow).where(JobRow.user_id == user_id, JobRow.org_id.is_(None))
            if before is not None:
                query = query.where(_before_clause(*before))
            rows = session.scalars(
                query.order_by(JobRow.created_at.desc(), JobRow.id.desc()).limit(limit)
            ).all()
            return [_record_from_row(row) for row in rows]

    def list_for_org(
        self,
        org_id: str,
        *,
        limit: int = 50,
        before: tuple[datetime, str] | None = None,
    ) -> list[JobRecord]:
        with self._session() as session:
            query = select(JobRow).where(JobRow.org_id == org_id)
            if before is not None:
                query = query.where(_before_clause(*before))
            rows = session.scalars(
                query.order_by(JobRow.created_at.desc(), JobRow.id.desc()).limit(limit)
            ).all()
            return [_record_from_row(row) for row in rows]

    def count_started(self, *, user_id: str, org_id: str | None, since: datetime) -> int:
        with self._session() as session:
            query = (
                select(func.count())
                .select_from(JobRow)
                .where(JobRow.created_at >= since, _quota_clause())
            )
            if org_id is not None:
                query = query.where(JobRow.org_id == org_id)
            else:
                query = query.where(JobRow.user_id == user_id, JobRow.org_id.is_(None))
            total = session.scalar(query)
            tombs = _tombstone_count(session, user_id=user_id, org_id=org_id, since=since)
            return int(total or 0) + tombs

    def discard(self, job_id: str, *, delete_object: Callable[[str], None]) -> DiscardState:
        with self._session() as session:
            row = session.scalar(select(JobRow).where(JobRow.id == job_id).with_for_update())
            if row is None:
                return DiscardState.missing
            if row.status == JobStatus.processing.value:
                return DiscardState.busy
            key = row.object_key
            # Two deletes of the same bytes take this lock in the same order.
            # The second sees the first row already gone and is the one that
            # erases the object. Creating another job does not take the lock.
            if session.get_bind().dialect.name == "postgresql":
                session.execute(
                    text(
                        "SELECT pg_advisory_xact_lock("
                        "hashtext('secureai-job-object'), hashtext(:object_key))"
                    ),
                    {"object_key": key},
                )
            others = session.scalar(
                select(func.count())
                .select_from(JobRow)
                .where(JobRow.object_key == key, JobRow.id != job_id)
            )
            record = _record_from_row(row)
            # Storage runs before the row is removed. A raise rolls the
            # transaction back on session close and leaves the job in place.
            if not others:
                delete_object(key)
            if _counts_toward_quota(record):
                session.add(
                    JobTombstoneRow(
                        job_id=row.id,
                        user_id=row.user_id,
                        org_id=row.org_id,
                        created_at=row.created_at,
                    )
                )
            session.delete(row)
            session.commit()
            return DiscardState.removed

    def claim(self, job_id: str) -> JobRecord | None:
        with self._session() as session:
            row = session.scalar(
                select(JobRow).where(JobRow.id == job_id).with_for_update()
            )
            if row is None or row.status != JobStatus.queued.value:
                return None
            row.status = JobStatus.processing.value
            row.attempt = row.attempt + 1
            row.updated_at = _now()
            session.commit()
            return _record_from_row(row)

    def release(self, job_id: str, *, attempt: int | None = None) -> bool:
        with self._session() as session:
            row = session.scalar(select(JobRow).where(JobRow.id == job_id).with_for_update())
            if row is None or row.status != JobStatus.processing.value:
                return False
            if attempt is not None and row.attempt != attempt:
                return False
            row.status = JobStatus.queued.value
            row.updated_at = _now()
            session.commit()
            return True

    def complete(
        self,
        job_id: str,
        *,
        prediction: str,
        confidence: float,
        attempt: int | None = None,
        detail: str | None = None,
    ) -> JobRecord | None:
        return self._finish(
            job_id,
            status=JobStatus.completed.value,
            prediction=prediction,
            confidence=confidence,
            detail=detail,
            attempt=attempt,
            require_processing=True,
        )

    def fail(
        self,
        job_id: str,
        *,
        attempt: int | None = None,
        detail: str | None = None,
    ) -> JobRecord | None:
        return self._finish(
            job_id,
            status=JobStatus.failed.value,
            prediction=None,
            confidence=None,
            detail=detail or PUBLIC_FAILURE_DETAIL,
            attempt=attempt,
            require_processing=attempt is not None,
        )

    def _finish(
        self,
        job_id: str,
        *,
        status: str,
        prediction: str | None,
        confidence: float | None,
        detail: str | None,
        attempt: int | None,
        require_processing: bool,
    ) -> JobRecord | None:
        with self._session() as session:
            # Lock the row so the status check and the write commit together.
            row = session.scalar(select(JobRow).where(JobRow.id == job_id).with_for_update())
            if row is None or not _can_finish(
                _record_from_row(row),
                attempt=attempt,
                require_processing=require_processing,
            ):
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
