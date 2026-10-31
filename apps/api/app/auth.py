"""Clerk auth placeholder.

Phase 1 replaces this with JWT verification against Clerk's JWKS. Until then
every request is accepted and the bearer token is not parsed.
"""

import logging
from typing import Annotated

from fastapi import Header

from secureai_shared.models import AuthContext

logger = logging.getLogger("secureai.api.auth")


def require_user(
    authorization: Annotated[str | None, Header()] = None,
) -> AuthContext:
    """Return a stub caller. Does not validate Clerk session JWTs.

    TODO(phase-1): require `Authorization: Bearer <clerk_jwt>`, verify the
    signature and expiry, and set subject from the `sub` claim. Missing or
    invalid tokens return 401. Never log the raw token.
    """

    if authorization is None:
        user = AuthContext(subject="anonymous")
    else:
        user = AuthContext(subject="unverified")
    logger.debug("auth subject=%s mode=%s", user.subject, user.mode)
    return user
