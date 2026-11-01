"""Resolve the workspace on a request.

The header is X-Org-Id. Clerk Organizations are not used; membership is a
Postgres row for a Clerk user id.
"""

from __future__ import annotations

import re

from fastapi import HTTPException, Request

from secureai_shared.models import AuthContext

ORG_ID = re.compile(r"org_[a-f0-9]{12}")


def active_org(request: Request, user: AuthContext) -> str | None:
    raw = request.headers.get("x-org-id")
    if raw is None or raw == "":
        return None
    if ORG_ID.fullmatch(raw) is None:
        raise HTTPException(status_code=400, detail="Invalid organization")
    role = request.app.state.billing.membership(raw, user.subject)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    return raw
