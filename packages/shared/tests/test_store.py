import os

import pytest

from secureai_shared.models import JobStatus
from secureai_shared.storage import new_object_key
from secureai_shared.store import PUBLIC_FAILURE_DETAIL, MemoryJobStore, PostgresJobStore


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


def test_postgres_round_trip() -> None:
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

        Base.metadata.create_all(store.engine)
    except Exception as exc:
        pytest.skip(f"postgres unavailable: {exc}")

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
