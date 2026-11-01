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

from app.billing_routes import router as billing_router
from app.migrate import run_migrations
from app.routes import router
from app.stripe_client import StripeBilling
from app.webhook_routes import router as webhook_router
from secureai_shared.billing import BillingStore, MemoryBillingStore, PostgresBillingStore
from secureai_shared.limits import RateLimiter, build_limiter
from secureai_shared.queue import JobQueue, build_queue
from secureai_shared.settings import Settings, assert_explicit_origins, load_settings
from secureai_shared.storage import FileSystemStorage, S3Storage, build_storage
from secureai_shared.store import JobStore, PostgresJobStore
from secureai_shared.webhook_queue import WebhookQueue, build_webhook_queue
from secureai_shared.webhooks import MemoryWebhookStore, PostgresWebhookStore, WebhookStore

logger = logging.getLogger("secureai.api")


def create_app(
    settings: Settings | None = None,
    store: JobStore | None = None,
    queue: JobQueue | None = None,
    storage: FileSystemStorage | S3Storage | None = None,
    fetch_jwks: Callable[[], dict[str, object]] | None = None,
    limiter: RateLimiter | None = None,
    billing: BillingStore | None = None,
    stripe: StripeBilling | None = None,
    webhooks: WebhookStore | None = None,
    webhook_queue: WebhookQueue | None = None,
) -> FastAPI:
    """Build the API. Real Postgres, Redis, and storage are created only when omitted."""

    resolved = settings if settings is not None else load_settings(role="api")
    assert_explicit_origins(resolved.cors_origins)
    if resolved.auth_mode == "clerk" and not resolved.clerk_authorized_parties:
        logger.warning(
            "CLERK_AUTHORIZED_PARTIES is empty, so azp is not checked. "
            "Set it on a public API. An empty list is only for local Clerk."
        )

    if store is None:
        run_migrations(resolved.database_url)
        store = PostgresJobStore(resolved.database_url)
    if queue is None:
        queue = build_queue(resolved)
    if storage is None:
        storage = build_storage(resolved)
    if billing is None:
        if isinstance(store, PostgresJobStore):
            billing = PostgresBillingStore(engine=store.engine)
        else:
            billing = MemoryBillingStore()
    _warn_billing(resolved)

    app = FastAPI(
        title="SecureAI API",
        version="0.5.0",
        description=(
            "Detection jobs require a verified Clerk session JWT. "
            "AUTH_MODE=dev accepts only Bearer dev and is a private-workstation "
            "bypass. Do not expose that mode on a public host. "
            "POST /v1/jobs/batch queues several stored objects in one request. "
            "If the queue stops after some ids are accepted, the 202 body "
            "lists those jobs and the ids that did not queue. "
            "GET /v1/jobs/{id}/report downloads a completed job as JSON. "
            "PDF export is not available yet. "
            "Plan quotas apply unless QUOTA_MODE=unlimited. "
            "Workspace owners can register one HTTPS webhook for terminal jobs."
        ),
    )
    app.state.settings = resolved
    app.state.store = store
    app.state.queue = queue
    app.state.storage = storage
    app.state.limiter = limiter if limiter is not None else build_limiter(resolved)
    if webhooks is None:
        if isinstance(store, PostgresJobStore):
            webhooks = PostgresWebhookStore(engine=store.engine)
        else:
            webhooks = MemoryWebhookStore()
    app.state.billing = billing
    app.state.stripe = stripe if stripe is not None else StripeBilling(resolved)
    app.state.webhooks = webhooks
    app.state.webhook_queue = webhook_queue if webhook_queue is not None else build_webhook_queue(resolved)
    app.state.fetch_jwks = fetch_jwks or _jwks_fetcher(resolved)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved.cors_origins),
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Org-Id"],
    )
    app.include_router(router)
    app.include_router(billing_router)
    app.include_router(webhook_router)
    return app


def _warn_billing(settings: Settings) -> None:
    if not settings.stripe_secret_key:
        if settings.quota_mode == "unlimited":
            logger.warning(
                "STRIPE_SECRET_KEY is empty and quotas are unlimited. "
                "Set STRIPE_SECRET_KEY for Checkout, or QUOTA_MODE=enforce to apply the free trial."
            )
        else:
            logger.warning(
                "STRIPE_SECRET_KEY is empty. Checkout and the Customer Portal are disabled. "
                "Callers stay on the free trial quota."
            )
        return
    if not settings.stripe_webhook_secret:
        logger.warning(
            "STRIPE_WEBHOOK_SECRET is empty. Checkout can start, but subscription "
            "updates will be rejected until the webhook secret is set."
        )


def _jwks_fetcher(settings: Settings) -> Callable[[], dict[str, object]]:
    cache: dict[str, object] = {"expires": 0.0, "body": None}

    def load(*, force: bool) -> dict[str, object]:
        now = time.time()
        body = cache["body"]
        if not force and isinstance(body, dict) and now < float(cache["expires"]):
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

    def fetch() -> dict[str, object]:
        return load(force=False)

    def refresh() -> dict[str, object]:
        return load(force=True)

    fetch.refresh = refresh  # type: ignore[attr-defined]
    return fetch
