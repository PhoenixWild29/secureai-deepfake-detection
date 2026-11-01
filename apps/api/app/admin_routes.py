"""Operator health. Public ``GET /health`` stays a liveness check.

This route is for a person on ``ADMIN_USER_IDS``. It is not the Railway
healthcheck. A failing dependency must not restart the API.
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth import require_admin
from secureai_shared.health import collect_dependency_health
from secureai_shared.models import AuthContext

router = APIRouter()


class ComponentHealth(BaseModel):
    status: Literal["ok", "error"]
    latency_ms: float


class AdminHealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    storage_backend: Literal["filesystem", "s3"]
    postgres: ComponentHealth
    redis: ComponentHealth
    storage: ComponentHealth


@router.get(
    "/v1/admin/health",
    response_model=AdminHealthResponse,
    responses={503: {"model": AdminHealthResponse}},
)
def admin_health(
    request: Request,
    user: Annotated[AuthContext, Depends(require_admin)],
) -> JSONResponse:
    """Report Postgres, Redis, and object storage without credentials.

    ``200`` means every check succeeded. ``503`` means the caller is an
    admin and at least one dependency did not answer. The body has no URL,
    bucket, or key. A signed-in non-admin, including an API key, is 404.
    """

    del user
    report = collect_dependency_health(
        request.app.state.store,
        request.app.state.queue,
        request.app.state.storage,
    )
    body = AdminHealthResponse(
        status=report.status,
        storage_backend=request.app.state.settings.storage_backend,
        postgres=ComponentHealth(
            status=report.postgres.status,
            latency_ms=report.postgres.latency_ms,
        ),
        redis=ComponentHealth(
            status=report.redis.status,
            latency_ms=report.redis.latency_ms,
        ),
        storage=ComponentHealth(
            status=report.storage.status,
            latency_ms=report.storage.latency_ms,
        ),
    )
    code = 200 if report.status == "ok" else 503
    return JSONResponse(status_code=code, content=body.model_dump())
