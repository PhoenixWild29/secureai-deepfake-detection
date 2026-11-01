"""Resolve the workspace on a request.

The header is X-Org-Id. Clerk Organizations are not used; membership is a
Postgres row for a Clerk user id.
"""

from __future__ import annotations

import re

from fastapi import HTTPException, Request

from secureai_shared.api_keys import may_use_api_key
from secureai_shared.billing import effective_plan
from secureai_shared.models import AuthContext

ORG_ID = re.compile(r"org_[a-f0-9]{12}")

# Minting a workspace key and presenting one both require this live role.
# A member, or a removed user, cannot hold a working workspace key.
WORKSPACE_MANAGER_ROLES = frozenset({"owner", "admin"})

API_KEY_PLAN_REQUIRED = "API keys require a Pro or Team plan."


def active_org(request: Request, user: AuthContext) -> str | None:
    """Workspace selected for this request.

    A bound API key is forced to its workspace. A personal key uses
    ``X-Org-Id`` the same way a session does. Session callers are not
    plan-gated here. An API key is: the workspace plan when one is
    selected, otherwise the personal plan.
    """

    org_id = _requested_org(request, user)
    if user.mode == "api_key":
        ensure_api_key_plan(request.app.state.billing, user.subject, org_id)
    return org_id


def _requested_org(request: Request, user: AuthContext) -> str | None:
    raw = request.headers.get("x-org-id")
    bound = user.api_key_org_id
    if bound:
        if raw not in (None, "") and raw != bound:
            raise HTTPException(status_code=403, detail="API key is limited to its workspace")
        raw = bound
    if raw is None or raw == "":
        return None
    if ORG_ID.fullmatch(raw) is None:
        raise HTTPException(status_code=400, detail="Invalid organization")
    role = request.app.state.billing.membership(raw, user.subject)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    return raw


def ensure_api_key_plan(billing: object, user_id: str, org_id: str | None) -> None:
    """402 unless this request's effective plan may use an API key.

    ``org_id`` is the workspace from ``X-Org-Id`` or the key binding.
    ``None`` is the personal account. The check is ``may_use_api_key`` on
    ``resolved_plan``: the paid half of ``may_issue_attestation``, with no
    dev-workstation bypass. Create and use both call this.
    """

    plan = resolved_plan(billing, user_id, org_id)
    if plan is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    if may_use_api_key(plan):
        return
    raise HTTPException(status_code=402, detail=API_KEY_PLAN_REQUIRED)


def resolved_plan(billing: object, user_id: str, org_id: str | None) -> str | None:
    """Effective plan for this subject, or None when ``org_id`` is not their workspace.

    Personal calls use the user account. ``past_due`` stays on the paid plan
    via ``effective_plan``. A missing billing row is the free plan.
    """

    if org_id is not None:
        summary = billing.org_summary(org_id, user_id=user_id)  # type: ignore[attr-defined]
        if summary is None:
            return None
        return effective_plan(summary.plan, summary.subscription_status)
    account = billing.user_account(user_id)  # type: ignore[attr-defined]
    return effective_plan(account.plan, account.subscription_status)
