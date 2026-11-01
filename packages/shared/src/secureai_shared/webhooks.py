"""Workspace webhook endpoints and at-least-once delivery.

Register stores one HTTPS URL per organization. A terminal job enqueues a
delivery id. The worker posts that JSON on another thread, so detection
does not wait on the customer's server. A secret, when set, signs the raw
body with HMAC-SHA256. The secret is stored in plaintext and is never
returned by the API.

Delivery resolves the hostname once and tries each validated address in
that order. Name lookup and TCP share the caller's timeout. Time spent
resolving is time later addresses do not get. A lookup that does not
finish in the time left does not open a socket. The lookup runs on a
daemon thread, so a stuck resolver cannot hold the delivery thread past
that timeout. Two lookups may be in flight. One organization holds at
most one of those slots, so a stuck lookup cannot take both. A caller
with no organization is limited the same way, by hostname. While this
attempt cannot take a slot, it waits one second and does not count.
After ``_DNS_BUSY_DEFERRAL_LIMIT`` of those waits, further busy results
count as failed attempts, so a lookup that never returns cannot defer
the delivery forever. A connect failure falls through to the next
address while time remains. That
remaining time is one budget for every TCP attempt, not a fresh timeout
per address. When that budget is spent, later addresses are not tried.
After a TCP connection succeeds, the TLS handshake and the HTTP exchange
share one deadline of the original timeout. Time spent in the handshake
is not available for the response, and each later read or write waits
only for the time still left. TLS and the Host header still use the
original hostname, so a DNS answer that changes
between the check and the connect cannot move the socket onto a private
address. A TLS failure does not try another address. Any TCP port is
accepted. A public address that proxies elsewhere is outside this check.
"""

from __future__ import annotations

import contextvars
import errno
import hashlib
import hmac
import io
import ipaddress
import json
import logging
import socket
import ssl
import sys
import threading
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from http import client as http_client
from typing import Protocol
from urllib.parse import urlsplit
from uuid import uuid4

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from secureai_shared.db import WebhookDeliveryRow, WebhookEndpointRow
from secureai_shared.models import JobRecord, JobStatus
from secureai_shared.webhook_queue import WebhookQueue

logger = logging.getLogger("secureai.webhooks")

SIGNATURE_HEADER = "X-SecureAI-Signature"
TIMESTAMP_HEADER = "X-SecureAI-Timestamp"
_USER_AGENT = "SecureAI-Webhooks/1"
_ERROR_LIMIT = 240

Post = Callable[[str, bytes, Mapping[str, str], float], int]


class WebhookConfigError(ValueError):
    """The URL or secret cannot be stored."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class WebhookResolverBusy(Exception):
    """This attempt cannot take a DNS slot.

    Every process slot is still in a lookup, or this organization (or the
    hostname, when delivery has no organization) already has one in flight.
    The delivery retries without counting until the busy cap.
    """


# libc getaddrinfo cannot be cancelled. A stuck lookup keeps its slot until
# it returns, on a daemon thread, and the delivery thread moves on.
# The process cap bounds how many of those threads exist. The per-key cap
# is one, so one organization cannot occupy both process slots. A third
# organization still waits when two lookups are already stuck. That wait
# is the busy deferral, and the deferral cap stops it from looping forever.
_DNS_LOOKUP_SLOTS = 2
_DNS_PER_KEY_SLOTS = 1
_DNS_BUSY_DELAY_SECONDS = 1.0
# Uncounted one-second waits recorded on the row. The next busy result counts.
# README.rebuild.md describes this number.
_DNS_BUSY_DEFERRAL_LIMIT = 30
_DNS_BUSY_ERROR = "DNS resolver is busy"
_DNS_SLOTS = threading.BoundedSemaphore(_DNS_LOOKUP_SLOTS)
_DNS_KEY_LOCK = threading.Lock()
_DNS_KEY_IN_FLIGHT: dict[str, int] = {}
_DNS_TENANT: contextvars.ContextVar[str] = contextvars.ContextVar(
    "secureai_webhook_dns_tenant",
    default="",
)


@dataclass(frozen=True)
class WebhookEndpoint:
    org_id: str
    url: str
    secret: str | None
    notify_failures: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class WebhookDelivery:
    id: str
    org_id: str
    job_id: str
    status: str
    attempt: int
    last_status_code: int | None
    last_error: str | None
    next_attempt_at: datetime
    payload: str
    delivering_until: datetime | None
    claim_token: str | None
    created_at: datetime
    updated_at: datetime


class WebhookStore(Protocol):
    def get_endpoint(self, org_id: str) -> WebhookEndpoint | None: ...

    def upsert_endpoint(
        self,
        *,
        org_id: str,
        url: str,
        secret: str | None,
        keep_secret: bool,
        notify_failures: bool | None,
    ) -> WebhookEndpoint: ...

    def delete_endpoint(self, org_id: str) -> bool: ...

    def create_delivery(
        self,
        *,
        org_id: str,
        job_id: str,
        payload: str,
        now: datetime,
    ) -> WebhookDelivery | None: ...

    def get_delivery(self, delivery_id: str) -> WebhookDelivery | None: ...

    def delivery_for_job(self, job_id: str) -> WebhookDelivery | None: ...

    def list_deliveries(self, org_id: str, *, limit: int = 20) -> list[WebhookDelivery]: ...

    def due_ids(self, now: datetime, *, limit: int = 50) -> list[str]: ...

    def begin_attempt(
        self,
        delivery_id: str,
        *,
        now: datetime,
        lease_seconds: float,
    ) -> WebhookDelivery | None: ...

    def record_result(
        self,
        delivery_id: str,
        *,
        claim_token: str,
        status: str,
        attempt: int,
        last_status_code: int | None,
        last_error: str | None,
        next_attempt_at: datetime,
        now: datetime,
    ) -> WebhookDelivery | None: ...


def signature_header(secret: str, timestamp: int, body: bytes) -> str:
    """HMAC-SHA256 over ``{timestamp}.{body}``. The header value is ``t=…,v1=…``."""

    signed = str(timestamp).encode("ascii") + b"." + body
    digest = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def retry_delay_seconds(attempt: int) -> float:
    """Wait after this many failed tries. The first failure waits 2 seconds."""

    if attempt < 1:
        return 2.0
    return min(300.0, 2.0 * (4 ** (attempt - 1)))


def event_body(job: JobRecord) -> str:
    """Stable JSON for one terminal job. Retries send these same bytes."""

    payload = {
        "confidence": job.confidence,
        "job_id": job.id,
        "org_id": job.org_id,
        "prediction": job.prediction,
        "status": job.status.value,
        "timestamp": _iso(job.updated_at),
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def validate_webhook_url(raw: str) -> str:
    """Accept one public https URL. Reject credentials, fragments, and private hosts."""

    if raw != raw.strip() or any(char in raw for char in ("\n", "\r", "\t", " ")):
        raise WebhookConfigError("Webhook URL must be an https URL.")
    if len(raw) > 2048:
        raise WebhookConfigError("Webhook URL must be an https URL.")
    parts = urlsplit(raw)
    host = parts.hostname
    if parts.scheme != "https" or not host or parts.username or parts.password or parts.fragment:
        raise WebhookConfigError("Webhook URL must be an https URL.")
    if parts.port == 0:
        raise WebhookConfigError("Webhook URL must be an https URL.")
    if _blocked_host(host):
        raise WebhookConfigError("Webhook URL must use a public https host.")
    return raw


def validate_secret(secret: str) -> str:
    if any(ord(char) < 32 for char in secret) or secret != secret.strip():
        raise WebhookConfigError("Webhook secret cannot include spaces at the ends or control characters.")
    if len(secret) < 16 or len(secret) > 256:
        raise WebhookConfigError("Webhook secret must be 16 to 256 characters.")
    return secret


def schedule_terminal(
    store: WebhookStore,
    queue: WebhookQueue,
    job: JobRecord,
    *,
    now: datetime | None = None,
) -> str | None:
    """Enqueue a delivery id. This does not open a socket.

    A missing endpoint, a personal job, or a failure the workspace opted out
    of returns None. A second call for the same job does not create a second
    row. Pending rows are published again so a crashed enqueue can be recovered
    by the next sweep.
    """

    if job.org_id is None or job.status not in {JobStatus.completed, JobStatus.failed}:
        return None
    endpoint = store.get_endpoint(job.org_id)
    if endpoint is None:
        return None
    if job.status is JobStatus.failed and not endpoint.notify_failures:
        return None
    clock = _clock(now)
    delivery = store.create_delivery(
        org_id=job.org_id,
        job_id=job.id,
        payload=event_body(job),
        now=clock,
    )
    if delivery is None:
        delivery = store.delivery_for_job(job.id)
        if delivery is None or delivery.status != "pending":
            return None if delivery is None else delivery.id
        if delivery.delivering_until is not None and delivery.delivering_until > clock:
            return delivery.id
    queue.publish(delivery.id, available_at=delivery.next_attempt_at.timestamp())
    logger.info("webhook scheduled job_id=%s delivery_id=%s", job.id, delivery.id)
    return delivery.id


def deliver_once(
    store: WebhookStore,
    queue: WebhookQueue,
    *,
    post: Post,
    timeout: float,
    max_attempts: int,
    now: datetime | None = None,
    lease_seconds: float = 30.0,
) -> bool:
    """Send one due delivery, or return False when nothing is due.

    Non-2xx responses and network errors stay pending until ``max_attempts``.
    The last status code and a short error are stored on the row.
    """

    clock = _clock(now)
    for delivery_id in store.due_ids(clock):
        queue.publish(delivery_id, available_at=clock.timestamp())
    claimed_id = queue.claim(now=clock.timestamp())
    if claimed_id is None:
        return False
    _deliver_claimed(
        store,
        queue,
        claimed_id,
        post=post,
        timeout=timeout,
        max_attempts=max_attempts,
        now=clock,
        lease_seconds=lease_seconds,
    )
    return True


def post_webhook(url: str, body: bytes, headers: Mapping[str, str], timeout: float) -> int:
    """POST JSON and return the status code. Redirects are not followed."""

    parts = urlsplit(url)
    host = parts.hostname
    if parts.scheme != "https" or not host:
        raise RuntimeError("webhook URL must be https")
    started = time.monotonic()
    addresses = _resolve_public_addresses(host, timeout=timeout)
    remaining = timeout - (time.monotonic() - started)
    if remaining <= 0:
        raise TimeoutError("webhook connect timed out")
    port = parts.port or 443
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    # ``host`` stays the URL hostname so the Host header and SNI match the
    # certificate. ``addresses`` are the IPs this call already accepted.
    # ``timeout`` stays the TLS budget. DNS time is removed from the TCP budget.
    connection = _PinnedHTTPSConnection(
        host,
        port,
        addresses=addresses,
        timeout=timeout,
        context=ssl.create_default_context(),
    )
    connection._connect_timeout = remaining
    try:
        connection.request("POST", path, body=body, headers=dict(headers))
        response = connection.getresponse()
        response.read(2048)
        return int(response.status)
    finally:
        connection.close()


def open_webhook_store(job_store: object) -> WebhookStore:
    """Use the job store's engine when it has one, otherwise an in-memory store."""

    engine = getattr(job_store, "engine", None)
    if engine is not None:
        return PostgresWebhookStore(engine=engine)
    return MemoryWebhookStore()


class MemoryWebhookStore:
    def __init__(self) -> None:
        self._endpoints: dict[str, WebhookEndpoint] = {}
        self._deliveries: dict[str, WebhookDelivery] = {}
        self._by_job: dict[str, str] = {}
        self._lock = threading.Lock()

    def get_endpoint(self, org_id: str) -> WebhookEndpoint | None:
        with self._lock:
            return self._endpoints.get(org_id)

    def upsert_endpoint(
        self,
        *,
        org_id: str,
        url: str,
        secret: str | None,
        keep_secret: bool,
        notify_failures: bool | None,
    ) -> WebhookEndpoint:
        now = _clock(None)
        with self._lock:
            current = self._endpoints.get(org_id)
            if current is None:
                endpoint = WebhookEndpoint(
                    org_id=org_id,
                    url=url,
                    secret=None if keep_secret else secret,
                    notify_failures=True if notify_failures is None else notify_failures,
                    created_at=now,
                    updated_at=now,
                )
            else:
                endpoint = replace(
                    current,
                    url=url,
                    secret=current.secret if keep_secret else secret,
                    notify_failures=current.notify_failures if notify_failures is None else notify_failures,
                    updated_at=now,
                )
            self._endpoints[org_id] = endpoint
            return endpoint

    def delete_endpoint(self, org_id: str) -> bool:
        with self._lock:
            return self._endpoints.pop(org_id, None) is not None

    def create_delivery(
        self,
        *,
        org_id: str,
        job_id: str,
        payload: str,
        now: datetime,
    ) -> WebhookDelivery | None:
        with self._lock:
            if job_id in self._by_job:
                return None
            delivery = WebhookDelivery(
                id=_new_delivery_id(),
                org_id=org_id,
                job_id=job_id,
                status="pending",
                attempt=0,
                last_status_code=None,
                last_error=None,
                next_attempt_at=now,
                payload=payload,
                delivering_until=None,
                claim_token=None,
                created_at=now,
                updated_at=now,
            )
            self._deliveries[delivery.id] = delivery
            self._by_job[job_id] = delivery.id
            return delivery

    def get_delivery(self, delivery_id: str) -> WebhookDelivery | None:
        with self._lock:
            return self._deliveries.get(delivery_id)

    def delivery_for_job(self, job_id: str) -> WebhookDelivery | None:
        with self._lock:
            delivery_id = self._by_job.get(job_id)
            if delivery_id is None:
                return None
            return self._deliveries.get(delivery_id)

    def list_deliveries(self, org_id: str, *, limit: int = 20) -> list[WebhookDelivery]:
        with self._lock:
            rows = [row for row in self._deliveries.values() if row.org_id == org_id]
        rows.sort(key=lambda row: row.updated_at, reverse=True)
        return rows[:limit]

    def due_ids(self, now: datetime, *, limit: int = 50) -> list[str]:
        with self._lock:
            due = [
                row.id
                for row in self._deliveries.values()
                if row.status == "pending" and row.next_attempt_at <= now and _lease_expired(row, now)
            ]
        due.sort()
        return due[:limit]

    def begin_attempt(
        self,
        delivery_id: str,
        *,
        now: datetime,
        lease_seconds: float,
    ) -> WebhookDelivery | None:
        with self._lock:
            row = self._deliveries.get(delivery_id)
            if not _can_claim(row, now):
                return None
            assert row is not None
            claimed = replace(
                row,
                delivering_until=now + timedelta(seconds=lease_seconds),
                claim_token=uuid4().hex,
                updated_at=now,
            )
            self._deliveries[delivery_id] = claimed
            return claimed

    def record_result(
        self,
        delivery_id: str,
        *,
        claim_token: str,
        status: str,
        attempt: int,
        last_status_code: int | None,
        last_error: str | None,
        next_attempt_at: datetime,
        now: datetime,
    ) -> WebhookDelivery | None:
        with self._lock:
            row = self._deliveries.get(delivery_id)
            if row is None or row.status != "pending" or row.claim_token != claim_token:
                return None
            updated = replace(
                row,
                status=status,
                attempt=attempt,
                last_status_code=last_status_code,
                last_error=_clip(last_error),
                next_attempt_at=next_attempt_at,
                delivering_until=None,
                claim_token=None,
                updated_at=now,
            )
            self._deliveries[delivery_id] = updated
            return updated


class PostgresWebhookStore:
    def __init__(self, database_url: str | None = None, engine: object | None = None) -> None:
        if engine is None:
            if not database_url:
                raise RuntimeError("PostgresWebhookStore requires a database url or an engine")
            from sqlalchemy import create_engine

            engine = create_engine(database_url, pool_pre_ping=True, hide_parameters=True)
        self.engine = engine
        self._session_factory = sessionmaker(engine, expire_on_commit=False)  # type: ignore[arg-type]

    def get_endpoint(self, org_id: str) -> WebhookEndpoint | None:
        with self._session() as session:
            row = session.get(WebhookEndpointRow, org_id)
            return None if row is None else _endpoint(row)

    def upsert_endpoint(
        self,
        *,
        org_id: str,
        url: str,
        secret: str | None,
        keep_secret: bool,
        notify_failures: bool | None,
    ) -> WebhookEndpoint:
        now = _clock(None)
        # Two creates for the same org can both observe a missing row. The
        # loser retries as an update instead of returning 500.
        for attempt in (1, 2):
            try:
                with self._session() as session:
                    row = session.get(WebhookEndpointRow, org_id)
                    if row is None:
                        row = WebhookEndpointRow(
                            org_id=org_id,
                            url=url,
                            secret=None if keep_secret else secret,
                            notify_failures=True if notify_failures is None else notify_failures,
                            created_at=now,
                            updated_at=now,
                        )
                        session.add(row)
                    else:
                        row.url = url
                        if not keep_secret:
                            row.secret = secret
                        if notify_failures is not None:
                            row.notify_failures = notify_failures
                        row.updated_at = now
                    session.flush()
                    return _endpoint(row)
            except IntegrityError:
                if attempt == 2:
                    raise
        raise RuntimeError("webhook endpoint upsert did not finish")

    def delete_endpoint(self, org_id: str) -> bool:
        with self._session() as session:
            row = session.get(WebhookEndpointRow, org_id)
            if row is None:
                return False
            session.delete(row)
            return True

    def create_delivery(
        self,
        *,
        org_id: str,
        job_id: str,
        payload: str,
        now: datetime,
    ) -> WebhookDelivery | None:
        row = WebhookDeliveryRow(
            id=_new_delivery_id(),
            org_id=org_id,
            job_id=job_id,
            status="pending",
            attempt=0,
            last_status_code=None,
            last_error=None,
            next_attempt_at=now,
            payload=payload,
            delivering_until=None,
            claim_token=None,
            created_at=now,
            updated_at=now,
        )
        try:
            with self._session() as session:
                session.add(row)
                session.flush()
                return _delivery(row)
        except IntegrityError:
            return None

    def get_delivery(self, delivery_id: str) -> WebhookDelivery | None:
        with self._session() as session:
            row = session.get(WebhookDeliveryRow, delivery_id)
            return None if row is None else _delivery(row)

    def delivery_for_job(self, job_id: str) -> WebhookDelivery | None:
        with self._session() as session:
            row = session.scalar(select(WebhookDeliveryRow).where(WebhookDeliveryRow.job_id == job_id))
            return None if row is None else _delivery(row)

    def list_deliveries(self, org_id: str, *, limit: int = 20) -> list[WebhookDelivery]:
        with self._session() as session:
            rows = session.scalars(
                select(WebhookDeliveryRow)
                .where(WebhookDeliveryRow.org_id == org_id)
                .order_by(WebhookDeliveryRow.updated_at.desc())
                .limit(limit)
            ).all()
            return [_delivery(row) for row in rows]

    def due_ids(self, now: datetime, *, limit: int = 50) -> list[str]:
        with self._session() as session:
            rows = session.scalars(
                select(WebhookDeliveryRow.id)
                .where(
                    WebhookDeliveryRow.status == "pending",
                    WebhookDeliveryRow.next_attempt_at <= now,
                    or_(
                        WebhookDeliveryRow.delivering_until.is_(None),
                        WebhookDeliveryRow.delivering_until <= now,
                    ),
                )
                .limit(limit)
            ).all()
            return list(rows)

    def begin_attempt(
        self,
        delivery_id: str,
        *,
        now: datetime,
        lease_seconds: float,
    ) -> WebhookDelivery | None:
        with self._session() as session:
            row = session.get(WebhookDeliveryRow, delivery_id, with_for_update=True)
            if row is None or not _can_claim(_delivery(row), now):
                return None
            row.delivering_until = now + timedelta(seconds=lease_seconds)
            row.claim_token = uuid4().hex
            row.updated_at = now
            session.flush()
            return _delivery(row)

    def record_result(
        self,
        delivery_id: str,
        *,
        claim_token: str,
        status: str,
        attempt: int,
        last_status_code: int | None,
        last_error: str | None,
        next_attempt_at: datetime,
        now: datetime,
    ) -> WebhookDelivery | None:
        with self._session() as session:
            row = session.get(WebhookDeliveryRow, delivery_id, with_for_update=True)
            if row is None or row.status != "pending" or row.claim_token != claim_token:
                return None
            row.status = status
            row.attempt = attempt
            row.last_status_code = last_status_code
            row.last_error = _clip(last_error)
            row.next_attempt_at = next_attempt_at
            row.delivering_until = None
            row.claim_token = None
            row.updated_at = now
            session.flush()
            return _delivery(row)

    @contextmanager
    def _session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


def _deliver_claimed(
    store: WebhookStore,
    queue: WebhookQueue,
    delivery_id: str,
    *,
    post: Post,
    timeout: float,
    max_attempts: int,
    now: datetime,
    lease_seconds: float,
) -> None:
    current = store.get_delivery(delivery_id)
    if current is None or current.status != "pending":
        return
    if current.next_attempt_at > now:
        queue.publish(delivery_id, available_at=current.next_attempt_at.timestamp())
        return
    if current.delivering_until is not None and current.delivering_until > now:
        queue.publish(delivery_id, available_at=current.delivering_until.timestamp())
        return
    claimed = store.begin_attempt(delivery_id, now=now, lease_seconds=lease_seconds)
    if claimed is None or claimed.claim_token is None:
        return
    endpoint = store.get_endpoint(claimed.org_id)
    if endpoint is None:
        store.record_result(
            claimed.id,
            claim_token=claimed.claim_token,
            status="failed",
            attempt=claimed.attempt + 1,
            last_status_code=None,
            last_error="Endpoint removed",
            next_attempt_at=now,
            now=now,
        )
        logger.info("webhook dropped delivery_id=%s reason=endpoint-removed", claimed.id)
        return
    body = claimed.payload.encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": _USER_AGENT,
    }
    timestamp = int(now.timestamp())
    if endpoint.secret:
        headers[TIMESTAMP_HEADER] = str(timestamp)
        headers[SIGNATURE_HEADER] = signature_header(endpoint.secret, timestamp, body)
    # post_webhook reads this. The DNS daemon thread does not. The key is
    # the organization, so one workspace cannot hold both process slots.
    tenant_token = _DNS_TENANT.set(claimed.org_id)
    try:
        code = post(endpoint.url, body, headers, timeout)
    except WebhookResolverBusy:
        _defer_busy(
            store,
            queue,
            claimed,
            now=now,
            max_attempts=max_attempts,
        )
        return
    except Exception as exc:
        logger.info("webhook post failed delivery_id=%s", claimed.id)
        _finish_failure(
            store,
            queue,
            claimed,
            now=now,
            max_attempts=max_attempts,
            code=None,
            error=_clip(f"{type(exc).__name__}: {exc}") or type(exc).__name__,
        )
        return
    finally:
        _DNS_TENANT.reset(tenant_token)
    if isinstance(code, int) and 200 <= code < 300:
        store.record_result(
            claimed.id,
            claim_token=claimed.claim_token,
            status="succeeded",
            attempt=claimed.attempt + 1,
            last_status_code=code,
            last_error=None,
            next_attempt_at=now,
            now=now,
        )
        logger.info("webhook delivered delivery_id=%s code=%s", claimed.id, code)
        return
    status_code = code if isinstance(code, int) else None
    error = f"HTTP {code}" if status_code is not None else "HTTP error"
    _finish_failure(
        store,
        queue,
        claimed,
        now=now,
        max_attempts=max_attempts,
        code=status_code,
        error=error,
    )


def _busy_error(deferrals: int) -> str:
    return f"{_DNS_BUSY_ERROR} ({deferrals})"


def _busy_deferrals_used(last_error: str | None) -> int:
    """How many uncounted busy waits this row has already stored.

    The count is the integer in ``DNS resolver is busy (N)``. Any other
    ``last_error``, including a counted network failure, starts again at
    zero. A worker restart keeps the count because it lives on the row.
    """

    if last_error is None:
        return 0
    prefix = f"{_DNS_BUSY_ERROR} ("
    if not last_error.startswith(prefix) or not last_error.endswith(")"):
        return 0
    number = last_error[len(prefix):-1]
    if not number.isdigit():
        return 0
    return int(number)


def _defer_busy(
    store: WebhookStore,
    queue: WebhookQueue,
    claimed: WebhookDelivery,
    *,
    now: datetime,
    max_attempts: int,
) -> None:
    """Put the row back without counting, until the busy cap.

    This delivery did not look up a name and did not open a socket. The
    next try waits one second. That wait does not count, up to
    ``_DNS_BUSY_DEFERRAL_LIMIT`` times, and the count stays in
    ``last_error``. The next busy result counts as a failed attempt and
    uses the normal retry wait. Further busy results keep counting, so a
    resolver that never returns reaches ``max_attempts`` and the row fails.
    """

    token = claimed.claim_token
    if token is None:
        return
    used = _busy_deferrals_used(claimed.last_error)
    if used >= _DNS_BUSY_DEFERRAL_LIMIT:
        logger.warning(
            "webhook dns busy counted delivery_id=%s deferrals=%s",
            claimed.id,
            used,
        )
        _finish_failure(
            store,
            queue,
            claimed,
            now=now,
            max_attempts=max_attempts,
            code=None,
            error=_busy_error(used),
        )
        return
    nxt = now + timedelta(seconds=_DNS_BUSY_DELAY_SECONDS)
    stored = store.record_result(
        claimed.id,
        claim_token=token,
        status="pending",
        attempt=claimed.attempt,
        last_status_code=None,
        last_error=_busy_error(used + 1),
        next_attempt_at=nxt,
        now=now,
    )
    if stored is None:
        return
    queue.publish(claimed.id, available_at=nxt.timestamp())
    logger.info("webhook dns busy delivery_id=%s deferrals=%s", claimed.id, used + 1)


def _finish_failure(
    store: WebhookStore,
    queue: WebhookQueue,
    claimed: WebhookDelivery,
    *,
    now: datetime,
    max_attempts: int,
    code: int | None,
    error: str,
) -> None:
    attempt = claimed.attempt + 1
    token = claimed.claim_token
    if token is None:
        return
    if attempt >= max_attempts:
        store.record_result(
            claimed.id,
            claim_token=token,
            status="failed",
            attempt=attempt,
            last_status_code=code,
            last_error=error,
            next_attempt_at=now,
            now=now,
        )
        logger.info("webhook gave up delivery_id=%s attempt=%s code=%s", claimed.id, attempt, code)
        return
    nxt = now + timedelta(seconds=retry_delay_seconds(attempt))
    stored = store.record_result(
        claimed.id,
        claim_token=token,
        status="pending",
        attempt=attempt,
        last_status_code=code,
        last_error=error,
        next_attempt_at=nxt,
        now=now,
    )
    if stored is None:
        return
    queue.publish(claimed.id, available_at=nxt.timestamp())
    logger.info("webhook retry delivery_id=%s attempt=%s code=%s", claimed.id, attempt, code)


def _can_claim(row: WebhookDelivery | None, now: datetime) -> bool:
    if row is None or row.status != "pending" or row.next_attempt_at > now:
        return False
    return _lease_expired(row, now)


def _lease_expired(row: WebhookDelivery, now: datetime) -> bool:
    return row.delivering_until is None or row.delivering_until <= now


def _blocked_host(host: str) -> bool:
    lowered = host.lower().rstrip(".")
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(
        (".local", ".internal", ".localhost")
    ):
        return True
    literal = _literal_ip(lowered)
    if literal is None:
        return False
    return not literal.is_global


def _connect_budget(timeout: object) -> float | None:
    """Seconds of shared connect budget, or None when there is no deadline.

    Delivery passes a numeric timeout. ``http.client`` stores
    ``socket._GLOBAL_DEFAULT_TIMEOUT`` when a connection is built without
    one. That sentinel is not a number. It is handled like ``None``: no
    deadline, and each TCP attempt blocks.
    """

    if timeout is None or timeout is socket._GLOBAL_DEFAULT_TIMEOUT:
        return None
    return float(timeout)  # type: ignore[arg-type]


class _DeadlineSocket:
    """Socket proxy whose reads and writes share one monotonic deadline.

    ``ssl.SSLSocket`` starts a new deadline from the current socket timeout
    on every handshake, read, and write. Setting that timeout once lets the
    handshake use the full budget and then lets the HTTP response use it
    again. Each call here waits only for the time still left.
    """

    def __init__(self, sock: socket.socket, deadline: float) -> None:
        self._sock = sock
        self._deadline = deadline

    def _arm(self) -> None:
        remaining = self._deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("webhook request timed out")
        self._sock.settimeout(remaining)

    def send(self, data: bytes | bytearray | memoryview, flags: int = 0) -> int:
        self._arm()
        return self._sock.send(data, flags)

    def sendall(self, data: bytes | bytearray | memoryview, flags: int = 0) -> None:
        view = memoryview(data)
        while view:
            sent = self.send(view, flags)
            if sent <= 0:
                raise ConnectionError("webhook send wrote no bytes")
            view = view[sent:]

    def recv(self, buflen: int, flags: int = 0) -> bytes:
        self._arm()
        return self._sock.recv(buflen, flags)

    def recv_into(
        self,
        buffer: bytearray | memoryview,
        nbytes: int | None = None,
        flags: int = 0,
    ) -> int:
        self._arm()
        # ``nbytes`` of 0 is a real length for ``ssl.SSLSocket`` only after
        # it replaces 0 with the buffer size. Pass ``None`` through so the
        # socket reads the buffer, which is what ``makefile`` asks for.
        if nbytes is None:
            return self._sock.recv_into(buffer)
        return self._sock.recv_into(buffer, nbytes, flags)

    def makefile(
        self,
        mode: str = "r",
        buffering: int | None = None,
        *,
        encoding: str | None = None,
        errors: str | None = None,
        newline: str | None = None,
    ) -> io.BufferedReader:
        del encoding, errors, newline
        if mode != "rb":
            raise ValueError("webhook deadline socket only supports binary reads")
        raw = socket.SocketIO(self, "rb")  # type: ignore[arg-type]
        if buffering is None or buffering < 0:
            buffering = io.DEFAULT_BUFFER_SIZE
        return io.BufferedReader(raw, buffering)

    def settimeout(self, value: object) -> None:
        # Callers cannot extend the deadline. The next I/O call arms the
        # time still left.
        del value

    def gettimeout(self) -> float:
        return max(0.0, self._deadline - time.monotonic())

    def fileno(self) -> int:
        return self._sock.fileno()

    def _decref_socketios(self) -> None:
        # ``socket.SocketIO.close`` drops a makefile reference on the real
        # socket. Closing the SSL socket is ``close`` below. This proxy has
        # no reference count of its own.
        return None

    def close(self) -> None:
        self._sock.close()


class _PinnedHTTPSConnection(http_client.HTTPSConnection):
    """TLS to ``host`` over addresses from one resolution, tried in order.

    Host and SNI stay ``host``. A TCP connect failure tries the next address
    while time remains in ``_connect_timeout``. That value defaults to
    ``timeout`` and is one budget shared by every address attempt. Delivery
    shortens it by the time DNS already used. Each attempt receives only the
    time still left. When the budget is spent, later addresses are not tried
    and the last connect error is raised. If the budget was already spent
    before any attempt, ``connect`` raises ``TimeoutError``. After TCP
    connects, one deadline of the original ``timeout`` covers the TLS
    handshake and the HTTP exchange. A later address does not shrink that
    deadline: DNS and TCP time stay in ``_connect_timeout``. Time spent in
    the handshake is not available for the response. A TLS failure,
    including a certificate failure, is not caught and does not try
    another address. The hostname is not resolved
    again. ``None`` disables the budget and each attempt blocks.
    ``socket._GLOBAL_DEFAULT_TIMEOUT``, which ``http.client`` stores when
    a connection is built without a timeout, is not a number and is
    treated the same way.
    """

    def __init__(
        self,
        host: str,
        port: int,
        *,
        addresses: Sequence[str],
        timeout: float,
        context: ssl.SSLContext,
    ) -> None:
        super().__init__(host, port, timeout=timeout, context=context)
        self._pinned_addresses = tuple(addresses)
        self._connect_timeout: object = timeout

    def connect(self) -> None:
        if not self._pinned_addresses:
            raise OSError("webhook connect has no pinned address")
        last_error: OSError | None = None
        # One monotonic deadline for every pinned address. ``create_connection``
        # treats a per-call timeout as "this attempt may block this long", so
        # passing the original timeout each time would allow N times the budget.
        # ``None`` and ``socket._GLOBAL_DEFAULT_TIMEOUT`` have no deadline.
        # The TLS handshake and the HTTP exchange share ``self.timeout`` as
        # one deadline. Delivery leaves that value at the caller's original
        # timeout after DNS has already reduced ``_connect_timeout``.
        budget = _connect_budget(self._connect_timeout)
        tls_budget = _connect_budget(self.timeout)
        deadline = None if budget is None else time.monotonic() + budget
        for address in self._pinned_addresses:
            if deadline is None:
                attempt_timeout: float | None = None
            else:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                attempt_timeout = remaining
            sys.audit("http.client.connect", self, address, self.port)
            try:
                sock = socket.create_connection(
                    (address, self.port),
                    attempt_timeout,
                    self.source_address,
                )
            except OSError as exc:
                last_error = exc
                continue
            self.sock = sock
            # The handshake and every later HTTP read or write share this
            # deadline. ``tls_budget`` is its length. It is not restarted
            # for the response, and a later address does not shorten it.
            request_deadline: float | None = None
            if tls_budget is not None and tls_budget > 0:
                request_deadline = time.monotonic() + tls_budget
                self.sock.settimeout(tls_budget)
            elif tls_budget is not None:
                self.sock.settimeout(tls_budget)
            try:
                self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            except OSError as exc:
                if exc.errno != errno.ENOPROTOOPT:
                    raise
            if self._tunnel_host:
                self._tunnel()
            server_hostname = self._tunnel_host or self.host
            self.sock = self._context.wrap_socket(self.sock, server_hostname=server_hostname)
            if request_deadline is not None:
                self.sock = _DeadlineSocket(self.sock, request_deadline)  # type: ignore[assignment]
            return
        if last_error is not None:
            raise last_error
        raise TimeoutError("webhook connect timed out")


def _dns_slot_key(host: str) -> str:
    """Organization when delivery set one, otherwise the hostname.

    Delivery sets ``_DNS_TENANT`` around ``post``. A direct ``post_webhook``
    call has no organization, so the hostname is the fairness key. One key
    holds at most ``_DNS_PER_KEY_SLOTS`` lookups.
    """

    tenant = _DNS_TENANT.get()
    if tenant:
        return "org:" + tenant
    return "host:" + host.lower().rstrip(".")


def _release_dns_key(key: str) -> None:
    with _DNS_KEY_LOCK:
        held = _DNS_KEY_IN_FLIGHT.get(key, 0) - 1
        if held <= 0:
            _DNS_KEY_IN_FLIGHT.pop(key, None)
        else:
            _DNS_KEY_IN_FLIGHT[key] = held


def _acquire_dns_slot(key: str) -> None:
    """Reserve one process slot and one slot for ``key``, or raise busy.

    The key is reserved first. A second caller for the same key loses
    even when a process slot is still free. If the process cap is full,
    the key reservation is rolled back so it does not leak.
    """

    with _DNS_KEY_LOCK:
        held = _DNS_KEY_IN_FLIGHT.get(key, 0)
        if held >= _DNS_PER_KEY_SLOTS:
            raise WebhookResolverBusy("webhook DNS resolver is busy")
        _DNS_KEY_IN_FLIGHT[key] = held + 1
    try:
        if not _DNS_SLOTS.acquire(blocking=False):
            raise WebhookResolverBusy("webhook DNS resolver is busy")
    except BaseException:
        _release_dns_key(key)
        raise


def _release_dns_slot(key: str) -> None:
    _release_dns_key(key)
    _DNS_SLOTS.release()


def _getaddrinfo_bounded(host: str, timeout: float) -> list:
    """Resolve ``host`` without holding the caller past ``timeout``.

    ``getaddrinfo`` has no deadline. It runs on a daemon thread that keeps
    its slot until it returns. The caller raises ``TimeoutError`` when the
    wait expires and leaves that thread alone. No free slot for this key
    raises ``WebhookResolverBusy`` immediately. The slot is released before
    the caller is woken, so the next lookup can take it.
    """

    if timeout <= 0:
        raise TimeoutError("webhook connect timed out")
    key = _dns_slot_key(host)
    _acquire_dns_slot(key)
    done = threading.Event()
    outcome_infos: list | None = None
    outcome_error: Exception | None = None

    def run() -> None:
        nonlocal outcome_infos, outcome_error
        try:
            outcome_infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        except Exception as exc:
            outcome_error = exc
        finally:
            try:
                _release_dns_slot(key)
            finally:
                done.set()

    thread = threading.Thread(target=run, name="secureai-webhook-dns", daemon=True)
    try:
        thread.start()
    except Exception:
        _release_dns_slot(key)
        raise
    if not done.wait(timeout):
        raise TimeoutError("webhook DNS timed out")
    if outcome_error is not None:
        raise outcome_error
    if outcome_infos is None:
        raise TimeoutError("webhook DNS timed out")
    return outcome_infos


def _resolve_public_addresses(host: str, *, timeout: float) -> list[str]:
    """Return every public address, in resolver order.

    Reject the host if any answer is not public. The caller tries the
    returned addresses and does not resolve again. ``timeout`` bounds the
    lookup. A non-positive timeout raises ``TimeoutError`` before any
    lookup, which is the same error as a connect budget that is already spent.
    """

    if _blocked_host(host):
        raise RuntimeError("webhook host is not a public address")
    literal = _literal_ip(host)
    if literal is not None:
        return [host]
    if timeout <= 0:
        raise TimeoutError("webhook connect timed out")
    try:
        infos = _getaddrinfo_bounded(host, timeout)
    except socket.gaierror as exc:
        raise RuntimeError("webhook host did not resolve") from exc
    if not infos:
        raise RuntimeError("webhook host did not resolve")
    chosen: list[str] = []
    seen: set[str] = set()
    for info in infos:
        raw = info[4][0]
        address = ipaddress.ip_address(raw.split("%", 1)[0])
        if not address.is_global:
            raise RuntimeError("webhook host is not a public address")
        if raw in seen:
            continue
        seen.add(raw)
        chosen.append(raw)
    if not chosen:
        raise RuntimeError("webhook host did not resolve")
    return chosen


def _literal_ip(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def _endpoint(row: WebhookEndpointRow) -> WebhookEndpoint:
    return WebhookEndpoint(
        org_id=row.org_id,
        url=row.url,
        secret=row.secret,
        notify_failures=bool(row.notify_failures),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _delivery(row: WebhookDeliveryRow) -> WebhookDelivery:
    return WebhookDelivery(
        id=row.id,
        org_id=row.org_id,
        job_id=row.job_id,
        status=row.status,
        attempt=row.attempt,
        last_status_code=row.last_status_code,
        last_error=row.last_error,
        next_attempt_at=row.next_attempt_at,
        payload=row.payload,
        delivering_until=row.delivering_until,
        claim_token=row.claim_token,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _new_delivery_id() -> str:
    return f"whd_{uuid4().hex[:12]}"


def _clock(now: datetime | None) -> datetime:
    clock = datetime.now(timezone.utc) if now is None else now
    if clock.tzinfo is None:
        return clock.replace(tzinfo=timezone.utc)
    return clock.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return _clock(value).isoformat()


def _clip(text: str | None) -> str | None:
    if text is None:
        return None
    cleaned = " ".join(text.split())
    if not cleaned:
        return None
    return cleaned[:_ERROR_LIMIT]
