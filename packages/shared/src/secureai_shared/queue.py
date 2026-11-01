"""Redis list of job ids plus an in-flight lease. Postgres holds the rows.

`consume` pops an id and writes its lease in one Lua script, so a crash
cannot drop an id that has left the list but is not yet leased. `BLMOVE`
of the list onto itself only wakes a blocking worker; it does not remove
the id. `claim_stale` refreshes a stale lease and republishes that id in
one script, and only when the attempt it observed is still current.
`ack` and `release` of a lease compare that attempt and its generation,
so a slow worker cannot delete a lease `claim_stale` has already refreshed.
Claiming a stale lease bumps the generation and keeps the attempt, which
stops the old ack from clearing the requeued lease and resetting the
attempt counter.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Protocol

from secureai_shared.settings import Settings

# Lease value is "<started>:<attempts>:<generation>". Pop and claim_stale
# each increment generation. Ack and renew of an older generation are no-ops,
# so they cannot clear or extend the lease claim_stale just wrote.
_LEASE_PARSE = """
local function parse_lease(raw)
  local sep = string.find(raw, ':', 1, true)
  if not sep then
    return nil
  end
  local started = tonumber(string.sub(raw, 1, sep - 1))
  local rest = string.sub(raw, sep + 1)
  local sep2 = string.find(rest, ':', 1, true)
  local attempts, generation
  if sep2 then
    attempts = tonumber(string.sub(rest, 1, sep2 - 1))
    generation = tonumber(string.sub(rest, sep2 + 1)) or 0
  else
    attempts = tonumber(rest)
    generation = 0
  end
  if not started or not attempts then
    return nil
  end
  return started, attempts, generation
end
"""

# RPOP and HSET run in one script. The id is on the lease before the script
# returns, and Redis applies the script atomically.
_POP_AND_LEASE = (
    _LEASE_PARSE
    + """
local job_id = redis.call('RPOP', KEYS[1])
if not job_id then
  return nil
end
local attempts = 0
local generation = 0
local raw = redis.call('HGET', KEYS[2], job_id)
if raw then
  local started, seen, gen = parse_lease(raw)
  if seen then
    attempts = seen
    generation = gen
  end
end
attempts = attempts + 1
generation = generation + 1
redis.call('HSET', KEYS[2], job_id, ARGV[1] .. ':' .. attempts .. ':' .. generation)
return {job_id, attempts, generation}
"""
)

# Compare the observed attempt and age, then refresh the lease and LPUSH.
# Generation changes so the worker that still holds the old one cannot ack
# this lease. The attempt count stays put until the next pop. A second
# sweeper sees a fresh timestamp and does not publish again.
_CLAIM_STALE = (
    _LEASE_PARSE
    + """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
if not raw then
  return 0
end
local started, attempts, generation = parse_lease(raw)
if not attempts or attempts ~= tonumber(ARGV[2]) then
  return 0
end
local now = tonumber(ARGV[3])
local lease = tonumber(ARGV[4])
if now - started < lease then
  return 0
end
generation = generation + 1
redis.call('HSET', KEYS[1], ARGV[1], ARGV[3] .. ':' .. attempts .. ':' .. generation)
redis.call('LPUSH', KEYS[2], ARGV[1])
return 1
"""
)

_ACK_ATTEMPT = (
    _LEASE_PARSE
    + """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
if not raw then
  return 0
end
local started, attempts, generation = parse_lease(raw)
if not attempts or attempts ~= tonumber(ARGV[2]) then
  return 0
end
local expected_gen = tonumber(ARGV[3])
if expected_gen >= 0 and generation ~= expected_gen then
  return 0
end
redis.call('HDEL', KEYS[1], ARGV[1])
return 1
"""
)

_RENEW_ATTEMPT = (
    _LEASE_PARSE
    + """
local raw = redis.call('HGET', KEYS[1], ARGV[1])
if not raw then
  return 0
end
local started, attempts, generation = parse_lease(raw)
if not attempts or attempts ~= tonumber(ARGV[2]) then
  return 0
end
local expected_gen = tonumber(ARGV[4])
if expected_gen >= 0 and generation ~= expected_gen then
  return 0
end
redis.call('HSET', KEYS[1], ARGV[1], ARGV[3] .. ':' .. attempts .. ':' .. generation)
return 1
"""
)


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
        self._inflight: dict[str, tuple[float, int] | tuple[float, int, int]] = {}
        # attempt, generation for the lease this process popped. Pruned on ack.
        self._held: dict[str, tuple[int, int]] = {}
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
            attempt, generation = self._touch_locked(job_id)
            self._held[job_id] = (attempt, generation)
            return job_id

    def held_attempt(self, job_id: str) -> int | None:
        local = self._held.get(job_id)
        if local is None:
            return None
        return local[0]

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
            _started, attempts, generation = _lease_parts(current)
            expected = self._expected(job_id, attempt)
            if expected is None or attempts != expected:
                return False
            if not self._generation_matches(job_id, expected, generation):
                return False
            self._inflight[job_id] = (time.time() if now is None else now, attempts, generation)
            return True

    def stale(self, older_than: float, *, now: float | None = None) -> list[tuple[str, int]]:
        clock = time.time() if now is None else now
        with self._mutex:
            found: list[tuple[str, int]] = []
            for job_id, raw in self._inflight.items():
                started, attempts, _generation = _lease_parts(raw)
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
            started, seen, generation = _lease_parts(current)
            if seen != attempts or clock - started < lease_seconds:
                return False
            # Keep the attempt. A new generation makes the popped worker's
            # ack a no-op, so it cannot drop this lease or restart the counter.
            self._inflight[job_id] = (clock, seen, generation + 1)
            self._ids.append(job_id)
            return True

    def _touch_locked(self, job_id: str, *, now: float | None = None) -> tuple[int, int]:
        clock = time.time() if now is None else now
        current = self._inflight.get(job_id)
        if current is None:
            attempts, generation = 0, 0
        else:
            _started, attempts, generation = _lease_parts(current)
        attempt = attempts + 1
        generation += 1
        self._inflight[job_id] = (clock, attempt, generation)
        return attempt, generation

    def _expected(self, job_id: str, attempt: int | None) -> int | None:
        if attempt is not None:
            return attempt
        local = self._held.get(job_id)
        if local is None:
            return None
        return local[0]

    def _generation_matches(self, job_id: str, expected: int, generation: int) -> bool:
        """False when this process still holds an older generation of `expected`.

        A caller with no local record (the sweeper) matches on the attempt
        alone. The worker that popped the old generation must not.
        """

        local = self._held.get(job_id)
        if local is None or local[0] != expected:
            return True
        return local[1] == generation

    def _drop_locked(self, job_id: str, attempt: int | None) -> bool:
        current = self._inflight.get(job_id)
        if current is None:
            self._forget_held(job_id, attempt)
            return False
        _started, attempts, generation = _lease_parts(current)
        expected = self._expected(job_id, attempt)
        if expected is None or attempts != expected:
            self._forget_held(job_id, attempt)
            return False
        if not self._generation_matches(job_id, expected, generation):
            self._forget_held(job_id, expected)
            return False
        self._inflight.pop(job_id, None)
        self._forget_held(job_id, expected)
        return True

    def _forget_held(self, job_id: str, attempt: int | None) -> None:
        local = self._held.get(job_id)
        if local is None:
            return
        if attempt is None or local[0] == attempt:
            self._held.pop(job_id, None)


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
        # attempt, generation for the lease this process popped. Pruned on ack.
        self._held: dict[str, tuple[int, int]] = {}
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
        job_id = str(result[0])
        attempt = int(result[1])
        generation = int(result[2]) if len(result) > 2 else 0
        self._held[job_id] = (attempt, generation)
        return job_id

    def held_attempt(self, job_id: str) -> int | None:
        local = self._held.get(job_id)
        if local is None:
            return None
        return local[0]

    def ack(self, job_id: str, *, attempt: int | None = None) -> bool:
        expected, generation = self._expected(job_id, attempt)
        if expected is None:
            return False
        removed = int(
            self._ack_attempt(keys=[self.inflight_key], args=[job_id, int(expected), int(generation)])
        )
        self._forget_held(job_id, expected)
        return removed == 1

    def renew(
        self,
        job_id: str,
        *,
        now: float | None = None,
        attempt: int | None = None,
    ) -> bool:
        expected, generation = self._expected(job_id, attempt)
        if expected is None:
            return False
        clock = time.time() if now is None else now
        updated = int(
            self._renew_attempt(
                keys=[self.inflight_key],
                args=[job_id, int(expected), int(clock), int(generation)],
            )
        )
        return updated == 1

    def stale(self, older_than: float, *, now: float | None = None) -> list[tuple[str, int]]:
        clock = time.time() if now is None else now
        found: list[tuple[str, int]] = []
        for job_id, raw in self.redis.hgetall(self.inflight_key).items():
            started, attempts, _generation = _parse_lease(raw)
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

    def _expected(self, job_id: str, attempt: int | None) -> tuple[int | None, int]:
        local = self._held.get(job_id)
        if attempt is None:
            if local is None:
                return None, -1
            return local[0], local[1]
        if local is not None and local[0] == attempt:
            return attempt, local[1]
        return attempt, -1

    def _forget_held(self, job_id: str, attempt: int | None) -> None:
        local = self._held.get(job_id)
        if local is None:
            return
        if attempt is None or local[0] == attempt:
            self._held.pop(job_id, None)

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


def _parse_lease(raw: str) -> tuple[float, int, int]:
    parts = raw.split(":")
    if len(parts) == 2:
        started, attempts = parts
        return float(started), int(attempts), 0
    started, attempts, generation = parts
    return float(started), int(attempts), int(generation)


def _lease_parts(raw: tuple[float, int] | tuple[float, int, int]) -> tuple[float, int, int]:
    if len(raw) == 2:
        started, attempts = raw
        return float(started), int(attempts), 0
    started, attempts, generation = raw
    return float(started), int(attempts), int(generation)


def build_queue(settings: Settings) -> JobQueue:
    if settings.queue_backend == "memory":
        return MemoryJobQueue()
    if settings.queue_backend == "redis":
        return RedisJobQueue(settings.redis_url, key=settings.queue_key)
    raise RuntimeError(f"Unsupported QUEUE_BACKEND={settings.queue_backend!r}")
