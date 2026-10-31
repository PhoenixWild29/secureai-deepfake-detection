"""Health and stub job routes."""

import logging
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.auth import require_user
from secureai_shared.models import AuthContext, JobRecord

logger = logging.getLogger("secureai.api.jobs")

JOB_ID = re.compile(r"job_[a-f0-9]{12}")

router = APIRouter()


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "secureai-api"


class JobCreate(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: str | None = Field(default=None, max_length=128)
    byte_size: int | None = Field(default=None, ge=0, le=50_000_000_000)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.post(
    "/v1/jobs",
    response_model=JobRecord,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_job(
    body: JobCreate,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> JobRecord:
    """Accept metadata and enqueue a stub job. Video bytes are not stored."""

    if user.mode != "stub":
        raise HTTPException(status_code=500, detail="Unexpected auth mode")
    job = request.app.state.queue.enqueue(
        filename=body.filename,
        content_type=body.content_type,
        byte_size=body.byte_size,
    )
    logger.info("enqueued job_id=%s subject=%s", job.id, user.subject)
    return job


@router.get("/v1/jobs/{job_id}", response_model=JobRecord)
def get_job(
    job_id: str,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> JobRecord:
    if user.mode != "stub":
        raise HTTPException(status_code=500, detail="Unexpected auth mode")
    if JOB_ID.fullmatch(job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job = request.app.state.queue.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
