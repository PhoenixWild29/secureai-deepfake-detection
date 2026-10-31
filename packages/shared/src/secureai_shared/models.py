"""Pydantic models shared by the API and the worker."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class JobRecord(BaseModel):
    """One detection ticket.

    Phase 0 stores these in process memory. Phase 1 persists them in Postgres
    and moves video bytes to object storage.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    filename: str
    content_type: str | None = None
    byte_size: int | None = None
    status: JobStatus = JobStatus.queued
    prediction: str | None = None
    confidence: float | None = None
    detail: str | None = None


class AuthContext(BaseModel):
    """Caller identity.

    `mode` stays `stub` until Phase 1 verifies Clerk session JWTs.
    """

    model_config = ConfigDict(frozen=True)

    subject: str
    mode: str = Field(default="stub")
