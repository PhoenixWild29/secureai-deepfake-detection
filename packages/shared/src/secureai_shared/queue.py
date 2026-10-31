"""Redis list of job ids. Postgres holds the rows. Memory is for unit tests."""

from __future__ import annotations

from collections import deque
from typing import Protocol

from secureai_shared.settings import Settings


class JobQueue(Protocol):
    def publish(self, job_id: str) -> None: ...

    def consume(self, timeout: float = 0) -> str | None: ...


class MemoryJobQueue:
    """Process-local id list. Two processes do not share it."""

    def __init__(self) -> None:
        self._ids: deque[str] = deque()

    def publish(self, job_id: str) -> None:
        self._ids.append(job_id)

    def consume(self, timeout: float = 0) -> str | None:
        del timeout
        if not self._ids:
            return None
        return self._ids.popleft()


class RedisJobQueue:
    """Shared queue. API LPUSHes ids; workers BRPOP them."""

    def __init__(self, url: str, *, key: str = "secureai:jobs") -> None:
        import redis

        if not url:
            raise RuntimeError("QUEUE_BACKEND=redis requires REDIS_URL")
        self.redis = redis.Redis.from_url(url, decode_responses=True)
        self.key = key

    def publish(self, job_id: str) -> None:
        self.redis.lpush(self.key, job_id)

    def consume(self, timeout: float = 0) -> str | None:
        if timeout <= 0:
            return self.redis.rpop(self.key)
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
        return job_id


def build_queue(settings: Settings) -> JobQueue:
    if settings.queue_backend == "memory":
        return MemoryJobQueue()
    if settings.queue_backend == "redis":
        return RedisJobQueue(settings.redis_url, key=settings.queue_key)
    raise RuntimeError(f"Unsupported QUEUE_BACKEND={settings.queue_backend!r}")
