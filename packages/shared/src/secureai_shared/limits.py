"""Fixed-window rate limits for upload and job creation."""

from __future__ import annotations

import threading
import time
from typing import Protocol

from secureai_shared.settings import Settings


class RateLimiter(Protocol):
    def allow(self, bucket: str, subject: str) -> bool: ...


class MemoryRateLimiter:
    def __init__(self, limits: dict[str, int], window_seconds: int) -> None:
        self.limits = limits
        self.window_seconds = window_seconds
        self._hits: dict[tuple[str, str], list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, bucket: str, subject: str) -> bool:
        limit = self.limits.get(bucket, 0)
        if limit <= 0:
            return True
        now = time.time()
        key = (bucket, subject)
        with self._lock:
            recent = [stamp for stamp in self._hits.get(key, []) if now - stamp < self.window_seconds]
            if len(recent) >= limit:
                self._hits[key] = recent
                return False
            recent.append(now)
            self._hits[key] = recent
            return True


class RedisRateLimiter:
    def __init__(self, url: str, limits: dict[str, int], window_seconds: int, *, prefix: str) -> None:
        import redis

        self.redis = redis.Redis.from_url(url, decode_responses=True)
        self.limits = limits
        self.window_seconds = window_seconds
        self.prefix = prefix

    def allow(self, bucket: str, subject: str) -> bool:
        limit = self.limits.get(bucket, 0)
        if limit <= 0:
            return True
        key = f"{self.prefix}:{bucket}:{subject}"
        count = int(self.redis.incr(key))
        if count == 1:
            self.redis.expire(key, self.window_seconds)
        return count <= limit


def build_limiter(settings: Settings) -> RateLimiter:
    limits = {
        "jobs": settings.rate_limit_jobs,
        "uploads": settings.rate_limit_uploads,
    }
    if settings.queue_backend == "redis" and settings.redis_url:
        return RedisRateLimiter(
            settings.redis_url,
            limits,
            settings.rate_limit_window_seconds,
            prefix=f"{settings.queue_key}:rl",
        )
    return MemoryRateLimiter(limits, settings.rate_limit_window_seconds)
