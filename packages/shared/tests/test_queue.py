import os
import time

import pytest

from secureai_shared.queue import MemoryJobQueue, RedisJobQueue, build_queue
from secureai_shared.settings import Settings


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "auth_mode": "dev",
        "clerk_issuer": "",
        "clerk_jwks_url": "",
        "clerk_authorized_parties": (),
        "database_url": "postgresql+psycopg://unused/unused",
        "redis_url": "",
        "queue_backend": "memory",
        "queue_key": "secureai:jobs",
        "storage_backend": "filesystem",
        "media_root": ".media",
        "s3_endpoint": "",
        "s3_bucket": "",
        "s3_access_key_id": "",
        "s3_secret_access_key": "",
        "s3_region": "us-east-1",
        "cors_origins": ("http://localhost:3000",),
        "dev_subject": "user_dev",
        "max_upload_bytes": 50_000_000,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def test_memory_queue_is_fifo_and_process_local() -> None:
    first = MemoryJobQueue()
    second = MemoryJobQueue()
    first.publish("job_a")
    first.publish("job_b")
    assert second.consume() is None
    assert first.consume() == "job_a"
    assert first.consume() == "job_b"
    assert first.consume() is None


def _assert_slow_ack_keeps_the_requeued_lease(queue) -> None:
    """Ack of the popped attempt must not drop the lease claim_stale refreshed."""

    queue.publish("job_slow")
    assert queue.consume() == "job_slow"
    first = queue.held_attempt("job_slow")
    assert first == 1
    later = time.time() + 30
    assert queue.claim_stale("job_slow", first, now=later, lease_seconds=10) is True
    assert queue.ack("job_slow", attempt=first) is False
    assert queue.stale(10, now=later + 30) == [("job_slow", 1)]
    assert queue.consume() == "job_slow"
    assert queue.held_attempt("job_slow") == 2
    assert queue.ack("job_slow", attempt=2) is True
    assert queue.held_attempt("job_slow") is None


def test_pop_and_stale_claim_are_single_scripts() -> None:
    scripts: list[str] = []

    class Redis:
        def register_script(self, script: str):
            scripts.append(script)

            def run(keys, args):  # noqa: ARG001
                return None

            return run

    RedisJobQueue("redis://unused", client=Redis())
    pop, claim, ack, renew = scripts
    assert "RPOP" in pop and "HSET" in pop
    assert "BLMOVE" not in pop
    assert "HSET" in claim and "LPUSH" in claim
    assert "ARGV[2]" in claim
    assert "generation" in claim
    assert "HDEL" in ack and "ARGV[2]" in ack
    assert "expected_gen" in ack
    assert "HSET" in renew and "ARGV[2]" in renew
    assert "expected_gen" in renew


def test_claim_stale_publishes_once_and_ack_keeps_a_newer_lease() -> None:
    queue = MemoryJobQueue()
    queue.publish("job_a")
    assert queue.consume() == "job_a"
    first = queue.held_attempt("job_a")
    assert first == 1
    later = time.time() + 30
    assert queue.claim_stale("job_a", first, now=later, lease_seconds=10) is True
    assert queue.claim_stale("job_a", first, now=later, lease_seconds=10) is False
    assert queue.consume() == "job_a"
    assert queue.consume() is None
    newer = queue.held_attempt("job_a")
    assert newer == 2
    assert queue.ack("job_a", attempt=first) is False
    assert queue.ack("job_a", attempt=newer) is True
    assert queue.held_attempt("job_a") is None
    assert queue._held == {}  # noqa: SLF001


def test_slow_worker_ack_after_claim_stale_does_not_reset_attempts() -> None:
    _assert_slow_ack_keeps_the_requeued_lease(MemoryJobQueue())


def test_build_queue_defaults_to_memory_when_configured() -> None:
    queue = build_queue(_settings())
    assert isinstance(queue, MemoryJobQueue)


def test_redis_publish_and_consume() -> None:
    url = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
    try:
        import redis

        client = redis.Redis.from_url(url, decode_responses=True)
        client.ping()
    except Exception as exc:
        if os.environ.get("REQUIRE_SERVICES") == "1":
            pytest.fail(f"redis unavailable: {exc}")
        pytest.skip(f"redis unavailable: {exc}")
    key = "secureai:jobs:unit"
    client.delete(key)
    client.delete(f"{key}:inflight")
    queue = RedisJobQueue(url, key=key)
    queue.publish("job_abc")
    assert queue.consume(timeout=0) == "job_abc"
    queue.ack("job_abc")
    assert queue.held_attempt("job_abc") is None
    assert queue._held == {}  # noqa: SLF001
    assert queue.consume(timeout=0) is None
    _assert_slow_ack_keeps_the_requeued_lease(RedisJobQueue(url, key=key))
    assert queue.consume(timeout=1) is None
    client.delete(key)
    client.delete(f"{key}:inflight")
