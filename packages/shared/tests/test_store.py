import os

import pytest
from sqlalchemy.exc import IntegrityError

from secureai_shared.models import JobStatus
from secureai_shared.storage import new_object_key
from secureai_shared.store import PUBLIC_FAILURE_DETAIL, MemoryJobStore, PostgresJobStore


def test_memory_create_many_rolls_back_the_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    store = MemoryJobStore()
    calls = {"n": 0}

    def new_id() -> str:
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("insert failed")
        return f"job_{calls['n']:012x}"

    monkeypatch.setattr("secureai_shared.store._new_id", new_id)
    key = new_object_key("user_a", "clip.mp4")
    try:
        store.create_many(
            user_id="user_a",
            org_id=None,
            items=[
                ("one.mp4", "video/mp4", 1, key, None),
                ("two.mp4", "video/mp4", 1, key, None),
            ],
        )
    except RuntimeError as exc:
        assert "insert failed" in str(exc)
    else:
        raise AssertionError("expected RuntimeError")
    assert store._rows == {}  # noqa: SLF001


def test_memory_store_hides_other_users_and_uses_fixed_failure() -> None:
    store = MemoryJobStore()
    key = new_object_key("user_a", "clip.mp4")
    created = store.create(
        user_id="user_a",
        filename="clip.mp4",
        content_type="video/mp4",
        byte_size=3,
        object_key=key,
    )
    assert created.status is JobStatus.queued
    assert store.get(created.id, user_id="user_b") is None
    claimed = store.claim(created.id)
    assert claimed is not None
    assert claimed.status is JobStatus.processing
    assert store.claim(created.id) is None
    failed = store.fail(created.id)
    assert failed is not None
    assert failed.detail == PUBLIC_FAILURE_DETAIL
    assert failed.status is JobStatus.failed


def _postgres_store() -> PostgresJobStore:
    """Open a throwaway schema, or skip when Postgres is not reachable.

    ``REQUIRE_SERVICES=1`` (CI) turns that skip into a failure.
    """

    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://secureai:secureai@127.0.0.1:5432/secureai",
    )
    try:
        store = PostgresJobStore(url)
        with store.engine.connect() as connection:
            connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS secureai_store_test")
            connection.commit()
        store.engine.dispose()
        schema_url = url + ("&" if "?" in url else "?") + "options=-csearch_path%3Dsecureai_store_test"
        store = PostgresJobStore(schema_url)
        from secureai_shared.db import Base

        Base.metadata.drop_all(store.engine)
        Base.metadata.create_all(store.engine)
    except Exception as exc:
        if os.environ.get("REQUIRE_SERVICES") == "1":
            pytest.fail(f"postgres unavailable: {exc}")
        pytest.skip(f"postgres unavailable: {exc}")
    return store


def test_postgres_round_trip() -> None:
    store = _postgres_store()
    key = new_object_key("user_pg", "clip.mp4")
    created = store.create(
        user_id="user_pg",
        filename="clip.mp4",
        content_type="video/mp4",
        byte_size=8,
        object_key=key,
    )
    assert store.get(created.id, user_id="someone_else") is None
    claimed = store.claim(created.id)
    assert claimed is not None
    finished = store.complete(created.id, prediction="real", confidence=0.8)
    assert finished is not None
    assert finished.prediction == "real"
    visible = store.get(created.id, user_id="user_pg")
    assert visible is not None
    assert visible.status is JobStatus.completed


def test_postgres_create_many_rolls_back_on_unique_violation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A primary-key collision on a later insert leaves none of the batch.

    The first two ids are new. The third reuses a row that is already
    committed, so Postgres rejects the statement. The earlier inserts in
    the same transaction must not remain.
    """

    store = _postgres_store()
    seed_key = new_object_key("user_pg", "seed.mp4")
    seed = store.create(
        user_id="user_pg",
        filename="seed.mp4",
        content_type="video/mp4",
        byte_size=4,
        object_key=seed_key,
        object_etag="etag-seed",
    )
    fresh = iter(("job_aa11bb22cc01", "job_aa11bb22cc02"))

    def new_id() -> str:
        try:
            return next(fresh)
        except StopIteration:
            return seed.id

    monkeypatch.setattr("secureai_shared.store._new_id", new_id)
    with pytest.raises(IntegrityError):
        store.create_many(
            user_id="user_pg",
            org_id=None,
            items=[
                ("one.mp4", "video/mp4", 4, new_object_key("user_pg", "one.mp4"), "etag-1"),
                ("two.mp4", "video/mp4", 4, new_object_key("user_pg", "two.mp4"), "etag-2"),
                ("three.mp4", "video/mp4", 4, new_object_key("user_pg", "three.mp4"), "etag-3"),
            ],
        )

    with store.engine.connect() as connection:
        names = [
            row[0]
            for row in connection.exec_driver_sql(
                "SELECT filename FROM jobs WHERE user_id = 'user_pg' ORDER BY filename"
            ).all()
        ]
    assert names == ["seed.mp4"]
    kept = store.get_any(seed.id)
    assert kept is not None
    assert kept.filename == "seed.mp4"
    assert kept.object_etag == "etag-seed"
    assert kept.status is JobStatus.queued
    assert store.get_any("job_aa11bb22cc01") is None
    assert store.get_any("job_aa11bb22cc02") is None
