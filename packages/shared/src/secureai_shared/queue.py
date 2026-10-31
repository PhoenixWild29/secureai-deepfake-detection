"""Redis list of job ids plus an in-flight lease. Postgres holds the rows."""

from __future__ import annotations

import time
from collections import deque
from typing import Protocol

from secureai_shared.settings import Settings


class JobQueue(Protocol):
    def publish(self, job_id: str) -> None: ...

    def consume(self, timeout: float = 0) -> str | None: ...

    def ack(self, job_id: str) -> None: ...

    def renew(self, job_id: str, *, now: float | None = None) -> None: ...

    def stale(self, older_than: float, *, now: float | None = None) -> list[tuple[str, int]]: ...


class MemoryJobQueue:
    """Process-local id list. Two processes do not share it."""

    def __init__(self) -> None:
        self._ids: deque[str] = deque()
        self._inflight: dict[str, tuple[float, int]] = {}

    def publish(self, job_id: str) -> None:
        self._ids.append(job_id)

    def consume(self, timeout: float = 0) -> str | None:
        del timeout
        if not self._ids:
            return None
        job_id = self._ids.popleft()
        self._touch(job_id)
        return job_id

    def ack(self, job_id: str) -> None:
        self._inflight.pop(job_id, None)

    def renew(self, job_id: str, *, now: float | None = None) -> None:
        current = self._inflight.get(job_id)
        if current is None:
            return
        _started, attempts = current
        self._inflight[job_id] = (time.time() if now is None else now, attempts)

    def stale(self, older_than: float, *, now: float | None = None) -> list[tuple[str, int]]:
        clock = time.time() if now is None else now
        found: list[tuple[str, int]] = []
        for job_id, (started, attempts) in self._inflight.items():
            if clock - started >= older_than:
                found.append((job_id, attempts))
        return found

    def _touch(self, job_id: str, *, now: float | None = None) -> None:
        clock = time.time() if now is None else now
        _started, attempts = self._inflight.get(job_id, (clock, 0))
        self._inflight[job_id] = (clock, attempts + 1)


class RedisJobQueue:
    """Shared queue. API LPUSHes ids; workers BRPOP them and record a lease."""

    def __init__(self, url: str, *, key: str = "secureai:jobs") -> None:
        import redis

        if not url:
            raise RuntimeError("QUEUE_BACKEND=redis requires REDIS_URL")
        self.redis = redis.Redis.from_url(url, decode_responses=True)
        self.key = key
        self.inflight_key = f"{key}:inflight"

    def publish(self, job_id: str) -> None:
        self.redis.lpush(self.key, job_id)

    def consume(self, timeout: float = 0) -> str | None:
        if timeout <= 0:
            job_id = self.redis.rpop(self.key)
        else:
            try:
                # redis-py can raise TimeoutError when BRPOP's socket wait ends
                # with no payload. That is an empty poll, not a dead queue.
                item = self.redis.brpop(self.key, timeout=max(1, int(timeout)))
            except Exception as exc:
                import redis

                if not isinstance(exc, redis.exceptions.TimeoutError):
                    raise
                return None
            if item is None:
                return None
            _key, job_id = item
        if job_id:
            self._touch(job_id)
        return job_id

    def ack(self, job_id: str) -> None:
        self.redis.hdel(self.inflight_key, job_id)

    def renew(self, job_id: str, *, now: float | None = None) -> None:
        raw = self.redis.hget(self.inflight_key, job_id)
        if not raw:
            return
        _started, attempts = _parse_lease(raw)
        clock = time.time() if now is None else now
        self.redis.hset(self.inflight_key, job_id, _lease(clock, attempts))

    def stale(self, older_than: float, *, now: float | None = None) -> list[tuple[str, int]]:
        clock = time.time() if now is None else now
        found: list[tuple[str, int]] = []
        for job_id, raw in self.redis.hgetall(self.inflight_key).items():
            started, attempts = _parse_lease(raw)
            if clock - started >= older_than:
                found.append((job_id, attempts))
        return found

    def _touch(self, job_id: str, *, now: float | None = None) -> None:
        clock = time.time() if now is None else now
        raw = self.redis.hget(self.inflight_key, job_id)
        attempts = _parse_lease(raw)[1] if raw else 0
        self.redis.hset(self.inflight_key, job_id, _lease(clock, attempts + 1))


def _lease(started: float, attempts: int) -> str:
    return f"{int(started)}:{attempts}"


def _parse_lease(raw: str) -> tuple[float, int]:
    started, attempts = raw.split(":", 1)
    return float(started), int(attempts)


def build_queue(settings: Settings) -> JobQueue:
    if settings.queue_backend == "memory":
        return MemoryJobQueue()
    if settings.queue_backend == "redis":
        return RedisJobQueue(settings.redis_url, key=settings.queue_key)
    raise RuntimeError(f"Unsupported QUEUE_BACKEND={settings.queue_backend!r}")
