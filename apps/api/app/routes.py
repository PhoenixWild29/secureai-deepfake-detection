"""Health, media upload, and job routes.

Job routes require a verified caller. Health stays public for platform checks.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from pydantic import BaseModel, Field

from app.auth import require_user
from app.batch_quota import accept_batch
from app.quota import accept_job
from app.tenancy import active_org
from secureai_shared.models import AuthContext, JobRecord, JobStatus
from secureai_shared.report import LIMITATIONS, load_report_detail
from secureai_shared.storage import ObjectStat, clean_filename, is_owned_key, new_object_key
from secureai_shared.store import UNQUEUED_FAILURE_DETAIL

logger = logging.getLogger("secureai.api.jobs")

JOB_ID = re.compile(r"job_[a-f0-9]{12}")

router = APIRouter()


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "secureai-api"
    auth: str


class UploadIntent(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=128)
    byte_size: int | None = Field(default=None, ge=0, le=50_000_000)


class UploadTicket(BaseModel):
    mode: Literal["direct", "presigned"]
    method: Literal["POST", "PUT"]
    upload_url: str
    object_key: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)
    fields: dict[str, str] = Field(default_factory=dict)


class MediaStored(BaseModel):
    object_key: str
    filename: str
    content_type: str | None
    byte_size: int


class JobCreate(BaseModel):
    object_key: str = Field(min_length=1, max_length=512)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=128)
    byte_size: int | None = Field(default=None, ge=0, le=50_000_000)


BATCH_MAX = 10


class BatchJobCreate(BaseModel):
    items: list[JobCreate] = Field(min_length=1, max_length=BATCH_MAX)


class BatchAccepted(BaseModel):
    jobs: list[JobRecord]


class JobReportExport(BaseModel):
    """JSON download for a completed job. PDF is not generated yet."""

    job_id: str
    filename: str
    status: str
    prediction: str | None
    confidence: float | None
    model: str | None
    signals: dict[str, float]
    limitations: str
    pdf_available: bool = False
    created_at: datetime
    updated_at: datetime


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    return HealthResponse(auth=request.app.state.settings.auth_mode)


@router.post("/v1/uploads", response_model=UploadTicket)
def create_upload(
    body: UploadIntent,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> UploadTicket:
    """Tell the client where to put bytes. Filesystem uses the API; S3 is a presigned POST."""

    _limit(request, "uploads", user.subject)
    try:
        filename = clean_filename(body.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid filename") from exc
    settings = request.app.state.settings
    if body.byte_size is not None and (
        body.byte_size < 1 or body.byte_size > settings.max_upload_bytes
    ):
        raise HTTPException(status_code=413, detail="Upload exceeds the size limit")

    storage = request.app.state.storage
    content_type = body.content_type or "application/octet-stream"
    if storage.supports_presign:
        key = new_object_key(user.subject, filename)
        ticket = storage.presign_post(key, content_type)
        if ticket is None:
            raise HTTPException(status_code=500, detail="Could not prepare upload")
        return UploadTicket(
            mode="presigned",
            method="POST",
            upload_url=ticket.url,
            object_key=key,
            fields=ticket.fields,
        )
    return UploadTicket(mode="direct", method="POST", upload_url="/v1/media")


@router.post("/v1/media", response_model=MediaStored)
async def upload_media(
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
    file: Annotated[UploadFile, File()],
) -> MediaStored:
    """Store bytes for the filesystem backend. S3 clients POST the presigned form instead."""

    _limit(request, "uploads", user.subject)
    settings = request.app.state.settings
    try:
        filename = clean_filename(file.filename or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid filename") from exc

    data = await file.read(settings.max_upload_bytes + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Upload exceeds the size limit")

    key = new_object_key(user.subject, filename)
    request.app.state.storage.put(key, data, file.content_type)
    logger.info("stored object subject=%s bytes=%s", user.subject, len(data))
    return MediaStored(
        object_key=key,
        filename=filename,
        content_type=file.content_type,
        byte_size=len(data),
    )


@router.post("/v1/jobs", response_model=JobRecord, status_code=status.HTTP_202_ACCEPTED)
def create_job(
    body: JobCreate,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> JobRecord:
    """Create a Postgres row for an object this caller already stored, then queue its id.

    The stored size and etag come from object storage. The client byte_size is ignored.
    If the queue rejects the id, the row is marked failed and does not count against
    the monthly quota. It is not left queued with no id in Redis.
    """

    _limit(request, "jobs", user.subject)
    filename, stat = _stored_upload(request, user, body)
    org_id = active_org(request, user)
    settings = request.app.state.settings
    job = accept_job(
        settings=settings,
        store=request.app.state.store,
        billing=request.app.state.billing,
        user_id=user.subject,
        org_id=org_id,
        filename=filename,
        content_type=body.content_type,
        byte_size=stat.size,
        object_key=body.object_key,
        object_etag=stat.etag,
    )
    _publish_or_fail(request, job)
    logger.info("enqueued job_id=%s subject=%s", job.id, user.subject)
    return job


@router.post("/v1/jobs/batch", response_model=BatchAccepted, status_code=status.HTTP_202_ACCEPTED)
def create_job_batch(
    body: BatchJobCreate,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> BatchAccepted:
    """Queue one job per stored object.

    Auth, ``X-Org-Id``, and the monthly quota match ``POST /v1/jobs``. The
    jobs rate limit is charged once per item after those items validate. Quota
    uses the same lock and cap as ``accept_job``, and the rows are inserted in
    one transaction. A bad item rejects the batch and inserts nothing.

    If publishing stops after one or more ids are queued, the response is
    still 202 and ``jobs`` lists those queued rows. Later rows are marked
    with the unqueued failure detail and do not spend quota.
    """

    org_id = active_org(request, user)
    prepared: list[tuple[JobCreate, str, ObjectStat]] = []
    seen: set[str] = set()
    for item in body.items:
        if item.object_key in seen:
            raise HTTPException(status_code=400, detail="Duplicate object key")
        seen.add(item.object_key)
        filename, stat = _stored_upload(request, user, item)
        prepared.append((item, filename, stat))
    _limit_times(request, "jobs", user.subject, len(prepared))
    jobs = accept_batch(
        settings=request.app.state.settings,
        store=request.app.state.store,
        billing=request.app.state.billing,
        user_id=user.subject,
        org_id=org_id,
        items=[
            (filename, item.content_type, stat.size, item.object_key, stat.etag)
            for item, filename, stat in prepared
        ],
    )
    published: list[JobRecord] = []
    for index, job in enumerate(jobs):
        try:
            _publish_or_fail(request, job)
        except HTTPException:
            for pending in jobs[index + 1 :]:
                try:
                    request.app.state.store.fail(pending.id, detail=UNQUEUED_FAILURE_DETAIL)
                except Exception:
                    logger.exception("could not fail unqueued job_id=%s", pending.id)
            if published:
                logger.error(
                    "batch publish stopped after %s of %s subject=%s",
                    len(published),
                    len(jobs),
                    user.subject,
                )
                break
            raise
        published.append(job)
        logger.info("enqueued job_id=%s subject=%s", job.id, user.subject)
    return BatchAccepted(jobs=published)


@router.get("/v1/jobs", response_model=list[JobRecord])
def list_jobs(
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> list[JobRecord]:
    org_id = active_org(request, user)
    if org_id is not None:
        return request.app.state.store.list_for_org(org_id, limit=50)
    return request.app.state.store.list_for_user(user.subject, limit=50)


@router.get("/v1/jobs/{job_id}", response_model=JobRecord)
def get_job(
    job_id: str,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> JobRecord:
    if JOB_ID.fullmatch(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    org_id = active_org(request, user)
    job = request.app.state.store.get(job_id, user_id=user.subject, org_id=org_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/v1/jobs/{job_id}/report", response_model=JobReportExport)
def export_job_report(
    job_id: str,
    request: Request,
    response: Response,
    user: Annotated[AuthContext, Depends(require_user)],
) -> JobReportExport:
    """Download a completed job as JSON.

    TODO: add a PDF body when a small renderer is chosen. ``pdf_available``
    stays false until then. The same route will keep returning this JSON.
    """

    job = get_job(job_id, request, user)
    if job.status is not JobStatus.completed:
        raise HTTPException(status_code=409, detail="Job is not complete")
    model, signals = load_report_detail(job.detail)
    response.headers["Content-Disposition"] = f'attachment; filename="{job.id}.json"'
    return JobReportExport(
        job_id=job.id,
        filename=job.filename,
        status=job.status.value,
        prediction=job.prediction,
        confidence=job.confidence,
        model=model,
        signals=signals,
        limitations=LIMITATIONS,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )


def _stored_upload(request: Request, user: AuthContext, body: JobCreate) -> tuple[str, ObjectStat]:
    try:
        filename = clean_filename(body.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid filename") from exc
    if not is_owned_key(user.subject, body.object_key):
        raise HTTPException(status_code=400, detail="Upload not found")
    stat = request.app.state.storage.object_stat(body.object_key)
    if stat is None:
        raise HTTPException(status_code=400, detail="Upload not found")
    if stat.size < 1 or stat.size > request.app.state.settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Upload exceeds the size limit")
    return filename, stat


def _limit(request: Request, bucket: str, subject: str) -> None:
    if not request.app.state.limiter.allow(bucket, subject):
        raise HTTPException(status_code=429, detail="Too many requests")


def _limit_times(request: Request, bucket: str, subject: str, times: int) -> None:
    for _index in range(times):
        _limit(request, bucket, subject)


def _publish_or_fail(request: Request, job: JobRecord) -> None:
    last: Exception | None = None
    for _attempt in range(3):
        try:
            request.app.state.queue.publish(job.id)
            return
        except Exception as exc:
            last = exc
    logger.error("enqueue failed job_id=%s", job.id, exc_info=last)
    try:
        # attempt stays 0. count_started skips this detail, so the 503 does not
        # spend a monthly job.
        request.app.state.store.fail(job.id, detail=UNQUEUED_FAILURE_DETAIL)
    except Exception:
        logger.exception("could not fail unqueued job_id=%s", job.id)
    raise HTTPException(status_code=503, detail="Could not queue the job") from last
