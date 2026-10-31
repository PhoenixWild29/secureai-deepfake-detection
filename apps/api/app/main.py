"""FastAPI entrypoint.

Importing this module does not connect to Postgres or Redis. Run:

    uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from collections.abc import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.migrate import run_migrations
from app.routes import router
from secureai_shared.queue import JobQueue, build_queue
from secureai_shared.settings import Settings, assert_explicit_origins, load_settings
from secureai_shared.storage import FileSystemStorage, S3Storage, build_storage
from secureai_shared.store import JobStore, PostgresJobStore

logger = logging.getLogger("secureai.api")


def create_app(
    settings: Settings | None = None,
    store: JobStore | None = None,
    queue: JobQueue | None = None,
    storage: FileSystemStorage | S3Storage | None = None,
    fetch_jwks: Callable[[], dict[str, object]] | None = None,
) -> FastAPI:
    """Build the API. Real Postgres, Redis, and storage are created only when omitted."""

    resolved = settings if settings is not None else load_settings(role="api")
    assert_explicit_origins(resolved.cors_origins)

    if store is None:
        run_migrations(resolved.database_url)
        store = PostgresJobStore(resolved.database_url)
    if queue is None:
        queue = build_queue(resolved)
    if storage is None:
        storage = build_storage(resolved)

    app = FastAPI(
        title="SecureAI API",
        version="0.2.0",
        description=(
            "Detection jobs require a verified Clerk session JWT. "
            "AUTH_MODE=dev accepts only Bearer dev and is a private-workstation "
            "bypass. Do not expose that mode on a public host."
        ),
    )
    app.state.settings = resolved
    app.state.store = store
    app.state.queue = queue
    app.state.storage = storage
    app.state.fetch_jwks = fetch_jwks or _jwks_fetcher(resolved)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(router)
    return app


def _jwks_fetcher(settings: Settings) -> Callable[[], dict[str, object]]:
    cache: dict[str, object] = {"expires": 0.0, "body": None}

    def fetch() -> dict[str, object]:
        now = time.time()
        body = cache["body"]
        if isinstance(body, dict) and now < float(cache["expires"]):
            return body
        url = settings.clerk_jwks_url or f"{settings.clerk_issuer}/.well-known/jwks.json"
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.load(response)
        if not isinstance(payload, dict):
            raise RuntimeError("JWKS payload was not an object")
        cache["body"] = payload
        cache["expires"] = now + 600
        logger.info("refreshed clerk jwks")
        return payload

    return fetch
