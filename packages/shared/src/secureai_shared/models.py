"""Pydantic models shared by the API and the worker."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class JobRecord(BaseModel):
    """One detection ticket persisted in Postgres."""

    model_config = ConfigDict(frozen=True)

    id: str
    user_id: str
    org_id: str | None = None
    filename: str
    content_type: str | None = None
    byte_size: int | None = None
    object_key: str
    object_etag: str | None = None
    status: JobStatus = JobStatus.queued
    prediction: str | None = None
    confidence: float | None = None
    detail: str | None = None
    attempt: int = 0
    created_at: datetime
    updated_at: datetime


class AuthContext(BaseModel):
    """Caller identity from a verified Clerk session JWT, or the local dev bypass."""

    model_config = ConfigDict(frozen=True)

    subject: str
    mode: str = Field(pattern="^(clerk|dev)$")
