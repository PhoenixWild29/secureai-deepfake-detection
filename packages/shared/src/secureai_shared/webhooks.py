"""Workspace webhook endpoints and at-least-once delivery.

Register stores one HTTPS URL per organization. A terminal job enqueues a
delivery id. The worker posts that JSON on another thread, so detection
does not wait on the customer's server. A secret, when set, signs the raw
body with HMAC-SHA256. The secret is never returned by the API.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import json
import logging
import socket
import ssl
import threading
from collections.abc import Callable, Iterator, Mapping
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
    _require_public_resolution(host)
    port = parts.port or 443
    path = parts.path or "/"
    if parts.query:
        path = f"{path}?{parts.query}"
    connection = http_client.HTTPSConnection(
        host,
        port,
        timeout=timeout,
        context=ssl.create_default_context(),
    )
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
    try:
        code = post(endpoint.url, body, headers, timeout)
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


def _require_public_resolution(host: str) -> None:
    if _blocked_host(host):
        raise RuntimeError("webhook host is not a public address")
    literal = _literal_ip(host)
    if literal is not None:
        return
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise RuntimeError("webhook host did not resolve") from exc
    if not infos:
        raise RuntimeError("webhook host did not resolve")
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            raise RuntimeError("webhook host is not a public address")


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
