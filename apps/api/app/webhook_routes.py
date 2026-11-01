"""Workspace webhook registration.

One HTTPS URL per organization. Owners and admins write it. Any member can
read the URL and delivery status. The signing secret is write-only.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import require_user
from app.tenancy import ORG_ID, ensure_api_key_org
from secureai_shared.models import AuthContext
from secureai_shared.webhooks import WebhookConfigError, WebhookDelivery, validate_secret, validate_webhook_url

logger = logging.getLogger("secureai.api.webhooks")

router = APIRouter()

_MANAGERS = frozenset({"owner", "admin"})


class WebhookWrite(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    secret: str | None = Field(default=None, max_length=256)
    notify_failures: bool | None = None


class DeliveryView(BaseModel):
    id: str
    job_id: str
    status: str
    attempt: int
    last_status_code: int | None
    last_error: str | None
    next_attempt_at: datetime
    updated_at: datetime


class WebhookView(BaseModel):
    org_id: str
    configured: bool
    url: str | None
    secret_set: bool
    notify_failures: bool
    can_manage: bool
    updated_at: datetime | None
    last_delivery: DeliveryView | None


def _role(request: Request, org_id: str, user: AuthContext) -> str:
    ensure_api_key_org(user, org_id)
    if ORG_ID.fullmatch(org_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    role = request.app.state.billing.membership(org_id, user.subject)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    return role


def _view(request: Request, org_id: str, role: str) -> WebhookView:
    endpoint = request.app.state.webhooks.get_endpoint(org_id)
    latest = request.app.state.webhooks.list_deliveries(org_id, limit=1)
    last = _delivery_view(latest[0]) if latest else None
    if endpoint is None:
        return WebhookView(
            org_id=org_id,
            configured=False,
            url=None,
            secret_set=False,
            notify_failures=True,
            can_manage=role in _MANAGERS,
            updated_at=None,
            last_delivery=last,
        )
    return WebhookView(
        org_id=org_id,
        configured=True,
        url=endpoint.url,
        secret_set=bool(endpoint.secret),
        notify_failures=endpoint.notify_failures,
        can_manage=role in _MANAGERS,
        updated_at=endpoint.updated_at,
        last_delivery=last,
    )


def _delivery_view(row: WebhookDelivery) -> DeliveryView:
    return DeliveryView(
        id=row.id,
        job_id=row.job_id,
        status=row.status,
        attempt=row.attempt,
        last_status_code=row.last_status_code,
        last_error=row.last_error,
        next_attempt_at=row.next_attempt_at,
        updated_at=row.updated_at,
    )


@router.get("/v1/orgs/{org_id}/webhook", response_model=WebhookView)
def get_webhook(
    org_id: str,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> WebhookView:
    role = _role(request, org_id, user)
    return _view(request, org_id, role)


@router.put("/v1/orgs/{org_id}/webhook", response_model=WebhookView)
def put_webhook(
    org_id: str,
    body: WebhookWrite,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> WebhookView:
    role = _role(request, org_id, user)
    if role not in _MANAGERS:
        raise HTTPException(status_code=403, detail="Only a workspace owner or admin can manage webhooks.")
    try:
        url = validate_webhook_url(body.url)
    except WebhookConfigError as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    existing = request.app.state.webhooks.get_endpoint(org_id)
    keep_secret = body.secret is None and existing is not None
    secret: str | None
    if keep_secret:
        secret = None
    elif body.secret is None or body.secret == "":
        secret = None
    else:
        try:
            secret = validate_secret(body.secret)
        except WebhookConfigError as exc:
            raise HTTPException(status_code=400, detail=exc.detail) from exc
    request.app.state.webhooks.upsert_endpoint(
        org_id=org_id,
        url=url,
        secret=secret,
        keep_secret=keep_secret,
        notify_failures=body.notify_failures,
    )
    logger.info("webhook saved org_id=%s subject=%s", org_id, user.subject)
    return _view(request, org_id, role)


@router.delete("/v1/orgs/{org_id}/webhook", status_code=204)
def delete_webhook(
    org_id: str,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> None:
    role = _role(request, org_id, user)
    if role not in _MANAGERS:
        raise HTTPException(status_code=403, detail="Only a workspace owner or admin can manage webhooks.")
    request.app.state.webhooks.delete_endpoint(org_id)
    logger.info("webhook removed org_id=%s subject=%s", org_id, user.subject)


@router.get("/v1/orgs/{org_id}/webhook/deliveries", response_model=list[DeliveryView])
def list_deliveries(
    org_id: str,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> list[DeliveryView]:
    _role(request, org_id, user)
    rows = request.app.state.webhooks.list_deliveries(org_id, limit=20)
    return [_delivery_view(row) for row in rows]
