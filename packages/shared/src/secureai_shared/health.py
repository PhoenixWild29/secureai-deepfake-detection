"""Readiness of Postgres, Redis, and object storage.

Results name the dependency and the outcome. They do not include URLs,
bucket names, keys, or exception text. Those often contain credentials.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from sqlalchemy import text

from secureai_shared.storage import FileSystemStorage, S3Storage

logger = logging.getLogger("secureai.health")

ProbeStatus = Literal["ok", "error"]
OverallStatus = Literal["ok", "degraded"]


@dataclass(frozen=True)
class Probe:
    status: ProbeStatus
    latency_ms: float


@dataclass(frozen=True)
class DependencyReport:
    status: OverallStatus
    postgres: Probe
    redis: Probe
    storage: Probe


def collect_dependency_health(store: object, queue: object, storage: object) -> DependencyReport:
    postgres = _probe("postgres", lambda: check_postgres(store))
    redis = _probe("redis", lambda: check_redis(queue))
    stored = _probe("storage", lambda: check_storage(storage))
    overall: OverallStatus = "ok"
    if "error" in {postgres.status, redis.status, stored.status}:
        overall = "degraded"
    return DependencyReport(status=overall, postgres=postgres, redis=redis, storage=stored)


def check_postgres(store: object) -> None:
    engine = getattr(store, "engine", None)
    if engine is None:
        raise RuntimeError("postgres unavailable")
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def check_redis(queue: object) -> None:
    client = getattr(queue, "redis", None)
    if client is None:
        raise RuntimeError("redis unavailable")
    client.ping()


def check_storage(storage: object) -> None:
    if isinstance(storage, FileSystemStorage):
        root = storage.root
        if not root.is_dir():
            raise RuntimeError("storage unavailable")
        probe = root / f".health-{uuid4().hex}"
        try:
            probe.write_bytes(b"ok")
        finally:
            probe.unlink(missing_ok=True)
        return
    if isinstance(storage, S3Storage):
        # HeadBucket is authorized as s3:ListBucket on AWS. PutObject alone
        # can still upload while this check reports error.
        storage.client.head_bucket(Bucket=storage.bucket)  # type: ignore[attr-defined]
        return
    raise RuntimeError("storage unavailable")


def _probe(name: str, fn: Callable[[], None]) -> Probe:
    started = time.perf_counter()
    try:
        fn()
    except Exception as exc:
        # The exception text can embed a URL. Keep the type only.
        logger.warning("%s health check failed (%s)", name, type(exc).__name__)
        return Probe(status="error", latency_ms=_latency(started))
    return Probe(status="ok", latency_ms=_latency(started))


def _latency(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 1)
