"""Health, media upload, and job routes.

Job routes require a verified caller. Health stays public for platform checks.
"""

from __future__ import annotations

import logging
import re
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field

from app.auth import require_user
from secureai_shared.models import AuthContext, JobRecord
from secureai_shared.storage import clean_filename, is_owned_key, new_object_key

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


class UploadTicket(BaseModel):
    mode: Literal["direct", "presigned"]
    method: Literal["POST", "PUT"]
    upload_url: str
    object_key: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)


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


@router.get("/health", response_model=HealthResponse)
def health(request: Request) -> HealthResponse:
    return HealthResponse(auth=request.app.state.settings.auth_mode)


@router.post("/v1/uploads", response_model=UploadTicket)
def create_upload(
    body: UploadIntent,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> UploadTicket:
    """Tell the client where to put bytes. Filesystem uses the API; S3 is presigned."""

    try:
        filename = clean_filename(body.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid filename") from exc

    storage = request.app.state.storage
    content_type = body.content_type or "application/octet-stream"
    if storage.supports_presign:
        key = new_object_key(user.subject, filename)
        url = storage.presign_put(key, content_type)
        if not url:
            raise HTTPException(status_code=500, detail="Could not prepare upload")
        return UploadTicket(
            mode="presigned",
            method="PUT",
            upload_url=url,
            object_key=key,
            headers={"Content-Type": content_type},
        )
    return UploadTicket(mode="direct", method="POST", upload_url="/v1/media")


@router.post("/v1/media", response_model=MediaStored)
async def upload_media(
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
    file: Annotated[UploadFile, File()],
) -> MediaStored:
    """Store bytes for the filesystem backend. S3 clients PUT the presigned URL instead."""

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
    """Create a Postgres row for an object this caller already stored, then queue its id."""

    try:
        filename = clean_filename(body.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid filename") from exc
    if not is_owned_key(user.subject, body.object_key):
        raise HTTPException(status_code=400, detail="Upload not found")
    if not request.app.state.storage.exists(body.object_key):
        raise HTTPException(status_code=400, detail="Upload not found")

    job = request.app.state.store.create(
        user_id=user.subject,
        filename=filename,
        content_type=body.content_type,
        byte_size=body.byte_size,
        object_key=body.object_key,
    )
    request.app.state.queue.publish(job.id)
    logger.info("enqueued job_id=%s subject=%s", job.id, user.subject)
    return job


@router.get("/v1/jobs/{job_id}", response_model=JobRecord)
def get_job(
    job_id: str,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> JobRecord:
    if JOB_ID.fullmatch(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job = request.app.state.store.get(job_id, user_id=user.subject)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
