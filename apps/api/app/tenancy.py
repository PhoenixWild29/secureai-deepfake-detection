"""Resolve the workspace on a request.

The header is X-Org-Id. Clerk Organizations are not used; membership is a
Postgres row for a Clerk user id.
"""

from __future__ import annotations

import re

from fastapi import HTTPException, Request

from secureai_shared.billing import effective_plan
from secureai_shared.models import AuthContext

ORG_ID = re.compile(r"org_[a-f0-9]{12}")


def active_org(request: Request, user: AuthContext) -> str | None:
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
