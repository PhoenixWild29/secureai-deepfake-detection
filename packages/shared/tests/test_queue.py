import os

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
    assert queue.consume(timeout=0) is None
    assert queue.consume(timeout=1) is None
    client.delete(key)
    client.delete(f"{key}:inflight")
