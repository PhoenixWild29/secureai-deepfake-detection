"""Redis sorted set of webhook delivery ids. Postgres holds the rows.

Score is the unix time the delivery may be attempted. A claim removes one
due id. Publishing the same id again updates that time, so a retry does
not create a second member.
"""

from __future__ import annotations

import threading
import time
from typing import Protocol

from secureai_shared.settings import Settings

_CLAIM_DUE = """
local ids = redis.call('ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1], 'LIMIT', 0, 1)
if #ids == 0 then
  return nil
end
redis.call('ZREM', KEYS[1], ids[1])
return ids[1]
"""


class WebhookQueue(Protocol):
    def publish(self, delivery_id: str, *, available_at: float) -> None: ...

    def claim(self, *, now: float) -> str | None: ...


class MemoryWebhookQueue:
    """Process-local delivery ids. Two processes do not share it."""

    def __init__(self) -> None:
        self._ready: dict[str, float] = {}
        self._lock = threading.Lock()

    def publish(self, delivery_id: str, *, available_at: float) -> None:
        with self._lock:
            self._ready[delivery_id] = available_at

    def claim(self, *, now: float) -> str | None:
        with self._lock:
            due = [item for item in self._ready.items() if item[1] <= now]
            if not due:
                return None
            due.sort(key=lambda item: (item[1], item[0]))
            chosen = due[0][0]
            del self._ready[chosen]
            return chosen


class RedisWebhookQueue:
    """Shared delivery queue. Score is the earliest unix time to send."""

    def __init__(self, url: str, *, key: str, client: object | None = None) -> None:
        if client is None:
            import redis

            if not url:
                raise RuntimeError("QUEUE_BACKEND=redis requires REDIS_URL")
            client = redis.Redis.from_url(url, decode_responses=True)
        self.redis = client
        self.key = key
        self._claim_due = client.register_script(_CLAIM_DUE)  # type: ignore[attr-defined]

    def publish(self, delivery_id: str, *, available_at: float) -> None:
        self.redis.zadd(self.key, {delivery_id: available_at})

    def claim(self, *, now: float) -> str | None:
        result = self._claim_due(keys=[self.key], args=[float(now)])
        if not result:
            return None
        return str(result)


def webhook_queue_key(settings: Settings) -> str:
    return f"{settings.queue_key}:webhooks"


def build_webhook_queue(settings: Settings) -> WebhookQueue:
    if settings.queue_backend == "memory":
        return MemoryWebhookQueue()
    if settings.queue_backend == "redis":
        return RedisWebhookQueue(settings.redis_url, key=webhook_queue_key(settings))
    raise RuntimeError(f"Unsupported QUEUE_BACKEND={settings.queue_backend!r}")


def queue_clock(now: float | None = None) -> float:
    return time.time() if now is None else now
