"""Create, list, and revoke Pro/Team API keys.

Personal keys belong to the signed-in user. Workspace keys belong to the
organization in ``X-Org-Id`` and can be managed by an owner or admin.
The plaintext secret is returned once from ``POST``. List and revoke never
include it or its hash.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import require_session
from app.tenancy import WORKSPACE_MANAGER_ROLES, active_org, ensure_api_key_plan
from secureai_shared.api_keys import ApiKeyLimit, ApiKeyNameError, ApiKeyRecord
from secureai_shared.models import AuthContext

logger = logging.getLogger("secureai.api.keys")

router = APIRouter()

_KEY_ID = re.compile(r"key_[a-f0-9]{12}")


class ApiKeyCreate(BaseModel):
    name: str = Field(default="API key", min_length=1, max_length=80)


class ApiKeyView(BaseModel):
    id: str
    name: str
    prefix: str
    org_id: str | None
    created_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None


class ApiKeyCreated(ApiKeyView):
    """``secret`` is the only response that contains the bearer token."""

    secret: str


def _view(row: ApiKeyRecord) -> ApiKeyView:
    return ApiKeyView(
        id=row.id,
        name=row.name,
        prefix=row.prefix,
        org_id=row.org_id,
        created_at=row.created_at,
        revoked_at=row.revoked_at,
        last_used_at=row.last_used_at,
    )


def _scope(request: Request, user: AuthContext) -> tuple[str | None, str]:
    org_id = active_org(request, user)
    if org_id is None:
        return None, "owner"
    role = request.app.state.billing.membership(org_id, user.subject)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    return org_id, role


def _require_manager(org_id: str | None, role: str) -> None:
    if org_id is not None and role not in WORKSPACE_MANAGER_ROLES:
        raise HTTPException(
            status_code=403,
            detail="Only a workspace owner or admin can manage API keys.",
        )


def _require_paid(request: Request, user: AuthContext, org_id: str | None) -> None:
    ensure_api_key_plan(request.app.state.billing, user.subject, org_id)


@router.get("/v1/api-keys", response_model=list[ApiKeyView])
def list_api_keys(
    request: Request,
    user: Annotated[AuthContext, Depends(require_session)],
) -> list[ApiKeyView]:
    """List keys for the personal account, or for the workspace in ``X-Org-Id``."""

    org_id, role = _scope(request, user)
    _require_manager(org_id, role)
    rows = request.app.state.api_keys.list_keys(user_id=user.subject, org_id=org_id)
    return [_view(row) for row in rows]


@router.post("/v1/api-keys", response_model=ApiKeyCreated, status_code=201)
def create_api_key(
    body: ApiKeyCreate,
    request: Request,
    user: Annotated[AuthContext, Depends(require_session)],
) -> ApiKeyCreated:
    """Mint a key. The secret is shown in this response and is not stored."""

    org_id, role = _scope(request, user)
    _require_manager(org_id, role)
    if not request.app.state.limiter.allow("api_keys", user.subject):
        raise HTTPException(status_code=429, detail="Too many requests")
    _require_paid(request, user, org_id)
    try:
        record, secret = request.app.state.api_keys.create(
            user_id=user.subject,
            org_id=org_id,
            name=body.name,
        )
    except ApiKeyNameError as exc:
        raise HTTPException(status_code=400, detail=exc.detail) from exc
    except ApiKeyLimit as exc:
        raise HTTPException(status_code=409, detail=exc.detail) from exc
    logger.info(
        "api key created id=%s prefix=%s subject=%s org_id=%s",
        record.id,
        record.prefix,
        user.subject,
        org_id or "-",
    )
    return ApiKeyCreated(
        id=record.id,
        name=record.name,
        prefix=record.prefix,
        org_id=record.org_id,
        created_at=record.created_at,
        revoked_at=record.revoked_at,
        last_used_at=record.last_used_at,
        secret=secret,
    )


@router.delete("/v1/api-keys/{key_id}", status_code=204)
def revoke_api_key(
    key_id: str,
    request: Request,
    user: Annotated[AuthContext, Depends(require_session)],
) -> None:
    """Revoke a key in the current personal or workspace context. It stops working immediately."""

    if _KEY_ID.fullmatch(key_id) is None:
        raise HTTPException(status_code=404, detail="API key not found")
    org_id, role = _scope(request, user)
    _require_manager(org_id, role)
    if not request.app.state.api_keys.revoke(key_id, user_id=user.subject, org_id=org_id):
        raise HTTPException(status_code=404, detail="API key not found")
    logger.info(
        "api key revoked id=%s subject=%s org_id=%s",
        key_id,
        user.subject,
        org_id or "-",
    )
