"""Dependency probes report ok or error and never echo credentials."""

from __future__ import annotations

from pathlib import Path

from secureai_shared.health import check_postgres, check_redis, check_storage, collect_dependency_health
from secureai_shared.storage import FileSystemStorage, S3Storage


class _Connection:
    def __enter__(self) -> _Connection:
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def execute(self, statement: object) -> None:
        assert "SELECT 1" in str(statement)


class _Engine:
    def connect(self) -> _Connection:
        return _Connection()


class _Store:
    def __init__(self, engine: object | None) -> None:
        self.engine = engine


class _Redis:
    def __init__(self, *, fail: BaseException | None = None) -> None:
        self.fail = fail
        self.pings = 0

    def ping(self) -> bool:
        self.pings += 1
        if self.fail is not None:
            raise self.fail
        return True


class _Queue:
    def __init__(self, client: object | None) -> None:
        self.redis = client


class _S3:
    def __init__(self) -> None:
        self.buckets: list[str] = []

    def head_bucket(self, *, Bucket: str) -> None:
        self.buckets.append(Bucket)


def test_collect_reports_ok_without_leaking_the_bucket() -> None:
    client = _S3()
    storage = S3Storage(client, "secret-bucket-name")
    report = collect_dependency_health(_Store(_Engine()), _Queue(_Redis()), storage)
    assert report.status == "ok"
    assert report.postgres.status == "ok"
    assert report.redis.status == "ok"
    assert report.storage.status == "ok"
    assert client.buckets == ["secret-bucket-name"]
    assert "secret-bucket-name" not in str(report)


def test_filesystem_probe_writes_and_removes_a_marker(tmp_path: Path) -> None:
    storage = FileSystemStorage(tmp_path)
    check_storage(storage)
    assert list(tmp_path.glob(".health-*")) == []


def test_failed_probe_omits_exception_text(tmp_path: Path) -> None:
    class SecretEngine:
        def connect(self) -> None:
            raise RuntimeError("postgresql://app:dbpassword@db.internal/app")

    redis = _Redis(fail=RuntimeError("redis://:supersecret@localhost:6379/0"))
    report = collect_dependency_health(
        _Store(SecretEngine()),
        _Queue(redis),
        FileSystemStorage(tmp_path),
    )
    assert report.status == "degraded"
    assert report.postgres.status == "error"
    assert report.redis.status == "error"
    assert report.storage.status == "ok"
    blob = str(report)
    assert "dbpassword" not in blob
    assert "supersecret" not in blob


def test_memory_backends_are_not_ready() -> None:
    class Memory:
        pass

    try:
        check_postgres(Memory())
    except RuntimeError as exc:
        assert "unavailable" in str(exc)
    else:
        raise AssertionError("expected postgres to fail closed")
    try:
        check_redis(Memory())
    except RuntimeError as exc:
        assert "unavailable" in str(exc)
    else:
        raise AssertionError("expected redis to fail closed")
