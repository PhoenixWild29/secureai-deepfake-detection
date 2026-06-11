"""Rate limiting for the FastAPI app (slowapi).

SECURITY: the detect endpoints run expensive ML inference and (for /url)
outbound downloads, so they must be rate limited per client. Limits are
env-configurable:

  RATE_LIMIT_DETECT        default "10/minute"  — single upload + URL analyze
  RATE_LIMIT_DETECT_BATCH  default "3/minute"   — batch analyze
  RATE_LIMIT_STORAGE_URI   default "memory://"  — set to your Redis URI
                           (e.g. "redis://:pass@redis:6379/1") so limits are
                           shared across gunicorn workers in production.

Keying: authenticated requests are keyed by user identity (JWT subject) when
available on request.state, otherwise by client IP.
"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

DETECT_LIMIT = os.getenv("RATE_LIMIT_DETECT", "10/minute")
DETECT_BATCH_LIMIT = os.getenv("RATE_LIMIT_DETECT_BATCH", "3/minute")
_STORAGE_URI = os.getenv("RATE_LIMIT_STORAGE_URI", "memory://")


def _key_func(request: Request) -> str:
    """Prefer the authenticated user id (set by the auth dependency) over IP."""
    user = getattr(request.state, "rate_limit_user", None)
    if user:
        return f"user:{user}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=_key_func,
    storage_uri=_STORAGE_URI,
    headers_enabled=True,  # X-RateLimit-* response headers
)
