import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import event, update
from sqlalchemy.exc import IntegrityError

from secureai_shared.db import JobRow
from secureai_shared.models import JobRecord, JobStatus
from secureai_shared.storage import new_object_key
from secureai_shared.store import (
    PUBLIC_FAILURE_DETAIL,
    UNQUEUED_FAILURE_DETAIL,
    DiscardState,
    MemoryJobStore,
    PostgresJobStore,
)


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


def _stamp_memory(store: MemoryJobStore, job: JobRecord, when: datetime) -> None:
    store._rows[job.id] = job.model_copy(update={"created_at": when})  # noqa: SLF001


def _stamp_postgres(store: PostgresJobStore, job: JobRecord, when: datetime) -> None:
    with store.engine.begin() as connection:
        connection.execute(update(JobRow).where(JobRow.id == job.id).values(created_at=when))


def _assert_history_pages(store: MemoryJobStore | PostgresJobStore, stamp) -> None:
    """Newest page, then the older page, including two rows that share a timestamp.

    A workspace job newer than every personal row stays off the personal pages.
    A personal row stays off the workspace page.
    """

    moment = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    older = store.create(
        user_id="user_a",
        filename="older.mp4",
        content_type="video/mp4",
        byte_size=1,
        object_key=new_object_key("user_a", "older.mp4"),
    )
    tied = store.create(
        user_id="user_a",
        filename="tied.mp4",
        content_type="video/mp4",
        byte_size=1,
        object_key=new_object_key("user_a", "tied.mp4"),
    )
    newest = store.create(
        user_id="user_a",
        filename="newest.mp4",
        content_type="video/mp4",
        byte_size=1,
        object_key=new_object_key("user_a", "newest.mp4"),
    )
    workspace = store.create(
        user_id="user_a",
        filename="workspace.mp4",
        content_type="video/mp4",
        byte_size=1,
        object_key=new_object_key("user_a", "workspace.mp4"),
        org_id="org_0123456789ab",
    )
    stamp(store, older, moment)
    stamp(store, tied, moment)
    stamp(store, newest, moment + timedelta(seconds=5))
    stamp(store, workspace, moment + timedelta(hours=1))

    # tied.id > older.id, so the shared timestamp orders tied ahead of older.
    assert tied.id > older.id
    first = store.list_for_user("user_a", limit=2)
    assert [job.id for job in first] == [newest.id, tied.id]
    second = store.list_for_user("user_a", limit=2, before=(first[-1].created_at, first[-1].id))
    assert [job.id for job in second] == [older.id]
    assert store.list_for_user("user_a", limit=2, before=(second[-1].created_at, second[-1].id)) == []
    org_page = store.list_for_org("org_0123456789ab", limit=2)
    assert [job.id for job in org_page] == [workspace.id]
    assert (
        store.list_for_org(
            "org_0123456789ab",
            limit=2,
            before=(org_page[0].created_at, org_page[0].id),
        )
        == []
    )


def test_memory_list_pages_past_a_shared_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    store = MemoryJobStore()
    ids = iter(
        (
            "job_00000000000a",
            "job_00000000000b",
            "job_00000000000c",
            "job_00000000000d",
        )
    )
    monkeypatch.setattr("secureai_shared.store._new_id", lambda: next(ids))
    _assert_history_pages(store, _stamp_memory)


def test_postgres_list_pages_past_a_shared_timestamp(monkeypatch: pytest.MonkeyPatch) -> None:
    store = _postgres_store()
    ids = iter(
        (
            "job_00000000000a",
            "job_00000000000b",
            "job_00000000000c",
            "job_00000000000d",
        )
    )
    monkeypatch.setattr("secureai_shared.store._new_id", lambda: next(ids))
    _assert_history_pages(store, _stamp_postgres)


def _explain(store: PostgresJobStore, call) -> str:
    """Run ``call`` and return ``EXPLAIN ANALYZE`` of the SELECT it issued."""

    captured: list[tuple[str, object]] = []

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):  # noqa: ARG001
        if statement.lstrip().upper().startswith("SELECT"):
            captured.append((statement, parameters))

    event.listen(store.engine, "before_cursor_execute", before_cursor_execute)
    try:
        call()
    finally:
        event.remove(store.engine, "before_cursor_execute", before_cursor_execute)
    assert captured, "expected a SELECT"
    statement, parameters = captured[-1]
    with store.engine.connect() as connection:
        raw = connection.connection.driver_connection
        with raw.cursor() as cursor:
            cursor.execute("EXPLAIN (ANALYZE, FORMAT TEXT) " + statement, parameters)
            lines = [row[0] for row in cursor.fetchall()]
    return "\n".join(lines)


def _assert_index_seek(plan: str, index: str, *, keyset: bool) -> None:
    assert index in plan
    assert "Index Cond" in plan
    assert "Sort Key" not in plan
    assert "Filter:" not in plan
    assert "Rows Removed by Filter" not in plan
    if keyset:
        assert "ROW(" in plan


def test_postgres_history_page_seeks_the_keyset_index() -> None:
    """A later page starts at the cursor. It does not sort every older row.

    About 8_000 rows is enough for Postgres 16 to prefer the composite index
    over a sequential scan. The cursor sits half an hour in, so a plan that
    filters from the newest row would drop thousands of index entries.
    """

    store = _postgres_store()
    with store.engine.begin() as connection:
        connection.exec_driver_sql(
            """
            INSERT INTO jobs (
                id, user_id, org_id, filename, content_type, byte_size, object_key,
                status, attempt, created_at, updated_at
            )
            SELECT
                'job_' || lpad(to_hex(i), 12, '0'),
                'user_page',
                CASE WHEN mod(i, 5) = 0 THEN 'org_0123456789ab' ELSE NULL END,
                'clip.mp4',
                'video/mp4',
                1,
                'media/user_page/' || i::text,
                'queued',
                0,
                timestamptz '2026-01-01 00:00:00+00' + (i || ' seconds')::interval,
                timestamptz '2026-01-01 00:00:00+00'
            FROM generate_series(1, 8000) AS s(i)
            """
        )
        connection.exec_driver_sql("ANALYZE jobs")

    personal_anchor = store.get_any(f"job_{1801:012x}")
    assert personal_anchor is not None
    assert personal_anchor.org_id is None
    personal_before = (personal_anchor.created_at, personal_anchor.id)
    personal_plan = _explain(
        store,
        lambda: store.list_for_user("user_page", limit=50, before=personal_before),
    )
    _assert_index_seek(personal_plan, "ix_jobs_personal_created_id", keyset=True)
    personal = store.list_for_user("user_page", limit=50, before=personal_before)
    assert len(personal) == 50
    assert all(job.org_id is None for job in personal)
    assert all((job.created_at, job.id) < personal_before for job in personal)
    assert personal == sorted(personal, key=lambda job: (job.created_at, job.id), reverse=True)

    first_plan = _explain(store, lambda: store.list_for_user("user_page", limit=50))
    _assert_index_seek(first_plan, "ix_jobs_personal_created_id", keyset=False)

    org_anchor = store.get_any(f"job_{4000:012x}")
    assert org_anchor is not None
    assert org_anchor.org_id == "org_0123456789ab"
    org_before = (org_anchor.created_at, org_anchor.id)
    org_plan = _explain(
        store,
        lambda: store.list_for_org("org_0123456789ab", limit=50, before=org_before),
    )
    _assert_index_seek(org_plan, "ix_jobs_org_created_id", keyset=True)
    org_page = store.list_for_org("org_0123456789ab", limit=50, before=org_before)
    assert len(org_page) == 50
    assert all(job.org_id == "org_0123456789ab" for job in org_page)
    assert all((job.created_at, job.id) < org_before for job in org_page)
    assert org_page == sorted(org_page, key=lambda job: (job.created_at, job.id), reverse=True)


def _exercise_discard(store: MemoryJobStore | PostgresJobStore) -> None:
    """Removing a job drops the row and keeps the monthly count.

    A shared object is erased only with the last job. A storage error leaves
    the row. A job that never reached the queue still does not count.
    Processing cannot be removed.
    """

    since = datetime(2020, 1, 1, tzinfo=timezone.utc)
    org_id = "org_0123456789ab"
    personal_key = new_object_key("user_a", "clip.mp4")
    personal = store.create(
        user_id="user_a",
        filename="secret-name.mp4",
        content_type="video/mp4",
        byte_size=4,
        object_key=personal_key,
        object_etag="etag-1",
    )
    shared_key = new_object_key("user_a", "shared.mp4")
    first = store.create(
        user_id="user_a",
        filename="shared.mp4",
        content_type="video/mp4",
        byte_size=4,
        object_key=shared_key,
        org_id=org_id,
    )
    second = store.create(
        user_id="user_b",
        filename="shared-again.mp4",
        content_type="video/mp4",
        byte_size=4,
        object_key=shared_key,
        org_id=org_id,
    )
    missed_key = new_object_key("user_a", "missed.mp4")
    missed = store.create(
        user_id="user_a",
        filename="missed.mp4",
        content_type="video/mp4",
        byte_size=4,
        object_key=missed_key,
    )
    assert store.fail(missed.id, detail=UNQUEUED_FAILURE_DETAIL) is not None
    busy_key = new_object_key("user_a", "busy.mp4")
    busy = store.create(
        user_id="user_a",
        filename="busy.mp4",
        content_type="video/mp4",
        byte_size=4,
        object_key=busy_key,
    )
    assert store.claim(busy.id) is not None
    fragile = store.create(
        user_id="user_a",
        filename="fragile.mp4",
        content_type="video/mp4",
        byte_size=4,
        object_key=new_object_key("user_a", "fragile.mp4"),
    )

    # personal, busy, and fragile count. missed never reached the queue.
    # Both workspace rows count for the org and not for a personal total.
    assert store.count_started(user_id="user_a", org_id=None, since=since) == 3
    assert store.count_started(user_id="user_a", org_id=org_id, since=since) == 2

    erased: list[str] = []
    assert store.discard(personal.id, delete_object=erased.append) is DiscardState.removed
    assert erased == [personal_key]
    assert store.get(personal.id, user_id="user_a") is None
    assert store.get_any(personal.id) is None
    assert store.claim(personal.id) is None
    assert {job.id for job in store.list_for_user("user_a")} == {missed.id, busy.id, fragile.id}
    assert store.discard(personal.id, delete_object=erased.append) is DiscardState.missing
    assert store.count_started(user_id="user_a", org_id=None, since=since) == 3

    assert store.discard(first.id, delete_object=erased.append) is DiscardState.removed
    assert shared_key not in erased
    kept = store.get_any(second.id)
    assert kept is not None
    assert kept.filename == "shared-again.mp4"
    assert store.discard(second.id, delete_object=erased.append) is DiscardState.removed
    assert erased[-1] == shared_key
    assert store.list_for_org(org_id) == []
    assert store.count_started(user_id="user_a", org_id=org_id, since=since) == 2
    assert store.count_started(user_id="user_b", org_id=None, since=since) == 0

    assert store.discard(missed.id, delete_object=erased.append) is DiscardState.removed
    assert erased[-1] == missed_key
    assert store.count_started(user_id="user_a", org_id=None, since=since) == 3

    def boom(_key: str) -> None:
        raise RuntimeError("disk")

    with pytest.raises(RuntimeError, match="disk"):
        store.discard(fragile.id, delete_object=boom)
    still = store.get_any(fragile.id)
    assert still is not None
    assert still.filename == "fragile.mp4"
    assert still.status is JobStatus.queued

    assert store.discard(busy.id, delete_object=erased.append) is DiscardState.busy
    assert busy_key not in erased
    still_busy = store.get_any(busy.id)
    assert still_busy is not None
    assert still_busy.status is JobStatus.processing


def test_memory_discard_keeps_quota_and_the_last_object() -> None:
    _exercise_discard(MemoryJobStore())


def test_postgres_discard_keeps_quota_and_the_last_object() -> None:
    _exercise_discard(_postgres_store())
