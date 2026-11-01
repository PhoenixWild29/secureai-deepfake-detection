"""Redis list of job ids plus an in-flight lease. Postgres holds the rows.

`consume` pops an id and writes its lease in one Lua script, so a crash
cannot drop an id that has left the list but is not yet leased. `BLMOVE`
of the list onto itself only wakes a blocking worker; it does not remove
the id. `claim_stale` refreshes a stale lease and republishes that id in
one script, and only when the attempt it observed is still current.
`ack` and `release` of a lease compare that attempt, so a slow worker
cannot delete a newer claim.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Protocol

from secureai_shared.settings import Settings

# RPOP and HSET run in one script. The id is on the lease before the script
# returns, and Redis applies the script atomically.
_POP_AND_LEASE = """
local job_id = redis.call('RPOP', KEYS[1])
if not job_id then
  return nil
end
local raw = redis.call('HGET', KEYS[2], job_id)
local attempts = 0
if raw then
  local sep = string.find(raw, ':', 1, true)
  if sep then
    attempts = tonumber(string.sub(raw, sep + 1)) or 0
  end
end
attempts = attempts + 1
redis.call('HSET', KEYS[2], job_id, ARGV[1] .. ':' .. attempts)
return {job_id, attempts}
"""

# Compare the observed attempt and age, then refresh the lease and LPUSH.
# A second sweeper sees a fresh timestamp and does not publish again.
_CLAIM_STALE = """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
if not raw then
  return 0
end
local sep = string.find(raw, ':', 1, true)
if not sep then
  return 0
end
local started = tonumber(string.sub(raw, 1, sep - 1))
local attempts = tonumber(string.sub(raw, sep + 1))
if attempts ~= tonumber(ARGV[2]) then
  return 0
end
local now = tonumber(ARGV[3])
local lease = tonumber(ARGV[4])
if now - started < lease then
  return 0
end
redis.call('HSET', KEYS[1], ARGV[1], ARGV[3] .. ':' .. ARGV[2])
redis.call('LPUSH', KEYS[2], ARGV[1])
return 1
"""

_ACK_ATTEMPT = """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
if not raw then
  return 0
end
local sep = string.find(raw, ':', 1, true)
if not sep then
  return 0
end
local attempts = tonumber(string.sub(raw, sep + 1))
if attempts ~= tonumber(ARGV[2]) then
  return 0
end
redis.call('HDEL', KEYS[1], ARGV[1])
return 1
"""

_RENEW_ATTEMPT = """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
if not raw then
  return 0
end
local sep = string.find(raw, ':', 1, true)
if not sep then
  return 0
end
local attempts = tonumber(string.sub(raw, sep + 1))
if attempts ~= tonumber(ARGV[2]) then
  return 0
end
redis.call('HSET', KEYS[1], ARGV[1], ARGV[3] .. ':' .. attempts)
return 1
"""


class JobQueue(Protocol):
    def publish(self, job_id: str) -> None: ...

    def consume(self, timeout: float = 0) -> str | None: ...

    def held_attempt(self, job_id: str) -> int | None: ...

    def ack(self, job_id: str, *, attempt: int | None = None) -> bool: ...

    def renew(self, job_id: str, *, now: float | None = None, attempt: int | None = None) -> bool: ...

    def stale(self, older_than: float, *, now: float | None = None) -> list[tuple[str, int]]: ...

    def claim_stale(
        self,
        job_id: str,
        attempts: int,
        *,
        now: float | None = None,
        lease_seconds: float,
    ) -> bool: ...


class MemoryJobQueue:
    """Process-local id list. Two processes do not share it."""

    def __init__(self) -> None:
        self._ids: deque[str] = deque()
        self._inflight: dict[str, tuple[float, int]] = {}
        self._held: dict[str, int] = {}
        self._mutex = threading.Lock()

    def publish(self, job_id: str) -> None:
        with self._mutex:
            self._ids.append(job_id)

    def consume(self, timeout: float = 0) -> str | None:
        del timeout
        with self._mutex:
            if not self._ids:
                return None
            job_id = self._ids.popleft()
            attempt = self._touch_locked(job_id)
            self._held[job_id] = attempt
            return job_id

    def held_attempt(self, job_id: str) -> int | None:
        return self._held.get(job_id)

    def ack(self, job_id: str, *, attempt: int | None = None) -> bool:
        with self._mutex:
            return self._drop_locked(job_id, attempt)

    def renew(
        self,
        job_id: str,
        *,
        now: float | None = None,
        attempt: int | None = None,
    ) -> bool:
        with self._mutex:
            current = self._inflight.get(job_id)
            if current is None:
                return False
            _started, attempts = current
            expected = self._expected(job_id, attempt)
            if expected is None or attempts != expected:
                return False
            self._inflight[job_id] = (time.time() if now is None else now, attempts)
            return True

    def stale(self, older_than: float, *, now: float | None = None) -> list[tuple[str, int]]:
        clock = time.time() if now is None else now
        with self._mutex:
            found: list[tuple[str, int]] = []
            for job_id, (started, attempts) in self._inflight.items():
                if clock - started >= older_than:
                    found.append((job_id, attempts))
            return found

    def claim_stale(
        self,
        job_id: str,
        attempts: int,
        *,
        now: float | None = None,
        lease_seconds: float,
    ) -> bool:
        clock = time.time() if now is None else now
        with self._mutex:
            current = self._inflight.get(job_id)
            if current is None:
                return False
            started, seen = current
            if seen != attempts or clock - started < lease_seconds:
                return False
            self._inflight[job_id] = (clock, seen)
            self._ids.append(job_id)
            return True

    def _touch_locked(self, job_id: str, *, now: float | None = None) -> int:
        clock = time.time() if now is None else now
        _started, attempts = self._inflight.get(job_id, (clock, 0))
        attempt = attempts + 1
        self._inflight[job_id] = (clock, attempt)
        return attempt

    def _expected(self, job_id: str, attempt: int | None) -> int | None:
        if attempt is not None:
            return attempt
        return self._held.get(job_id)

    def _drop_locked(self, job_id: str, attempt: int | None) -> bool:
        current = self._inflight.get(job_id)
        if current is None:
            return False
        expected = self._expected(job_id, attempt)
        if expected is None or current[1] != expected:
            return False
        self._inflight.pop(job_id, None)
        return True


class RedisJobQueue:
    """Shared queue. API LPUSHes ids; workers claim them with a lease."""

    def __init__(self, url: str, *, key: str = "secureai:jobs", client: object | None = None) -> None:
        if client is None:
            import redis

            if not url:
                raise RuntimeError("QUEUE_BACKEND=redis requires REDIS_URL")
            client = redis.Redis.from_url(url, decode_responses=True)
        self.redis = client
        self.key = key
        self.inflight_key = f"{key}:inflight"
        self._held: dict[str, int] = {}
        self._pop_lease = client.register_script(_POP_AND_LEASE)  # type: ignore[attr-defined]
        self._claim_stale = client.register_script(_CLAIM_STALE)  # type: ignore[attr-defined]
        self._ack_attempt = client.register_script(_ACK_ATTEMPT)  # type: ignore[attr-defined]
        self._renew_attempt = client.register_script(_RENEW_ATTEMPT)  # type: ignore[attr-defined]

    def publish(self, job_id: str) -> None:
        self.redis.lpush(self.key, job_id)

    def consume(self, timeout: float = 0) -> str | None:
        if timeout > 0 and not self._wait(timeout):
            return None
        result = self._pop_lease(keys=[self.key, self.inflight_key], args=[int(time.time())])
        if not result:
            return None
        job_id, attempts = result
        attempt = int(attempts)
        self._held[str(job_id)] = attempt
        return str(job_id)

    def held_attempt(self, job_id: str) -> int | None:
        return self._held.get(job_id)

    def ack(self, job_id: str, *, attempt: int | None = None) -> bool:
        expected = attempt if attempt is not None else self._held.get(job_id)
        if expected is None:
            return False
        removed = int(self._ack_attempt(keys=[self.inflight_key], args=[job_id, int(expected)]))
        return removed == 1

    def renew(
        self,
        job_id: str,
        *,
        now: float | None = None,
        attempt: int | None = None,
    ) -> bool:
        expected = attempt if attempt is not None else self._held.get(job_id)
        if expected is None:
            return False
        clock = time.time() if now is None else now
        updated = int(
            self._renew_attempt(keys=[self.inflight_key], args=[job_id, int(expected), int(clock)])
        )
        return updated == 1

    def stale(self, older_than: float, *, now: float | None = None) -> list[tuple[str, int]]:
        clock = time.time() if now is None else now
        found: list[tuple[str, int]] = []
        for job_id, raw in self.redis.hgetall(self.inflight_key).items():
            started, attempts = _parse_lease(raw)
            if clock - started >= older_than:
                found.append((job_id, attempts))
        return found

    def claim_stale(
        self,
        job_id: str,
        attempts: int,
        *,
        now: float | None = None,
        lease_seconds: float,
    ) -> bool:
        clock = time.time() if now is None else now
        won = int(
            self._claim_stale(
                keys=[self.inflight_key, self.key],
                args=[job_id, int(attempts), int(clock), float(lease_seconds)],
            )
        )
        return won == 1

    def _wait(self, timeout: float) -> bool:
        """Block until the list is non-empty without removing an id.

        BLMOVE of a list onto itself (RIGHT then RIGHT) returns the tail and
        pushes it back to the tail. The id stays on the list. The following
        Lua pop is what pairs the id with its lease.
        """

        try:
            peeked = self.redis.blmove(self.key, self.key, max(1, int(timeout)), "RIGHT", "RIGHT")
        except Exception as exc:
            import redis

            if not isinstance(exc, redis.exceptions.TimeoutError):
                raise
            return False
        return peeked is not None


def _parse_lease(raw: str) -> tuple[float, int]:
    started, attempts = raw.split(":", 1)
    return float(started), int(attempts)


def build_queue(settings: Settings) -> JobQueue:
    if settings.queue_backend == "memory":
        return MemoryJobQueue()
    if settings.queue_backend == "redis":
        return RedisJobQueue(settings.redis_url, key=settings.queue_key)
    raise RuntimeError(f"Unsupported QUEUE_BACKEND={settings.queue_backend!r}")
