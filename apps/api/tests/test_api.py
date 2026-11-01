from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from conftest import _client, make_settings
from secureai_shared.limits import MemoryRateLimiter
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.storage import new_object_key
from secureai_shared.settings import Settings
from secureai_shared.store import UNQUEUED_FAILURE_DETAIL


def test_import_does_not_connect() -> None:
    import app.main as main

    assert callable(main.create_app)
    assert not hasattr(main, "app")


def test_health_is_public_and_reports_auth_mode(stack) -> None:
    client, _, _, _ = stack
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "secureai-api", "auth": "dev"}


def test_job_routes_reject_anonymous_and_junk_tokens(stack) -> None:
    client, _, _, _ = stack
    missing = client.post("/v1/uploads", json={"filename": "clip.mp4"})
    assert missing.status_code == 401
    assert missing.json()["detail"] == "Authentication required"
    junk = client.get(
        "/v1/jobs/job_0123456789ab",
        headers={"Authorization": "Bearer not-a-jwt"},
    )
    assert junk.status_code == 401


def test_upload_and_queue_round_trip(stack) -> None:
    client, store, queue, _ = stack
    headers = {"Authorization": "Bearer dev"}
    uploaded = client.post(
        "/v1/media",
        headers=headers,
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )
    assert uploaded.status_code == 200
    media = uploaded.json()
    assert media["byte_size"] == len(b"video-bytes")
    created = client.post(
        "/v1/jobs",
        headers=headers,
        json={
            "object_key": media["object_key"],
            "filename": media["filename"],
            "content_type": media["content_type"],
            "byte_size": media["byte_size"],
        },
    )
    assert created.status_code == 202
    body = created.json()
    assert body["status"] == "queued"
    assert body["user_id"] == "user_dev"
    assert queue.consume() == body["id"]
    fetched = client.get(f"/v1/jobs/{body['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]
    assert store.get(body["id"], user_id="other") is None
    hidden = client.get(f"/v1/jobs/{body['id']}", headers=headers)
    assert hidden.status_code == 200


def test_other_user_cannot_read_a_job(stack) -> None:
    client, store, _, storage = stack
    key = new_object_key("user_other", "clip.mp4")
    storage.put(key, b"abc", "video/mp4")
    job = store.create(
        user_id="user_other",
        filename="clip.mp4",
        content_type="video/mp4",
        byte_size=3,
        object_key=key,
    )
    response = client.get(f"/v1/jobs/{job.id}", headers={"Authorization": "Bearer dev"})
    assert response.status_code == 404


def test_missing_and_malformed_jobs(stack) -> None:
    client, _, _, _ = stack
    headers = {"Authorization": "Bearer dev"}
    assert client.get("/v1/jobs/job_0123456789ab", headers=headers).status_code == 404
    assert client.get("/v1/jobs/not-a-job", headers=headers).status_code == 404


def test_rejects_unowned_or_missing_object(stack) -> None:
    client, _, queue, _ = stack
    headers = {"Authorization": "Bearer dev"}
    foreign = client.post(
        "/v1/jobs",
        headers=headers,
        json={"object_key": new_object_key("someone_else", "clip.mp4"), "filename": "clip.mp4"},
    )
    assert foreign.status_code == 400
    missing = client.post(
        "/v1/jobs",
        headers=headers,
        json={"object_key": new_object_key("user_dev", "clip.mp4"), "filename": "clip.mp4"},
    )
    assert missing.status_code == 400
    assert queue.consume() is None


def test_rejects_oversized_upload(limited_client: TestClient) -> None:
    response = limited_client.post(
        "/v1/media",
        headers={"Authorization": "Bearer dev"},
        files={"file": ("clip.mp4", b"12345", "video/mp4")},
    )
    assert response.status_code == 413


def test_filesystem_upload_ticket_is_direct(stack) -> None:
    client, _, _, _ = stack
    response = client.post(
        "/v1/uploads",
        headers={"Authorization": "Bearer dev"},
        json={"filename": "clip.mp4", "content_type": "video/mp4"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "direct"
    assert body["upload_url"] == "/v1/media"
    assert body["object_key"] is None


def test_cors_allows_local_guardian(stack) -> None:
    client, _, _, _ = stack
    response = client.options(
        "/v1/jobs",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_job_create_uses_stored_size(tmp_path: Path) -> None:
    client, _store, queue, storage = _client(tmp_path, make_settings(tmp_path, max_upload_bytes=4))
    key = new_object_key("user_dev", "clip.mp4")
    storage.put(key, b"12345", "video/mp4")
    with client:
        response = client.post(
            "/v1/jobs",
            headers={"Authorization": "Bearer dev"},
            json={"object_key": key, "filename": "clip.mp4", "byte_size": 1},
        )
    assert response.status_code == 413
    assert queue.consume() is None


def test_list_jobs_is_owner_scoped(stack) -> None:
    client, store, _queue, storage = stack
    headers = {"Authorization": "Bearer dev"}
    uploaded = client.post(
        "/v1/media",
        headers=headers,
        files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
    )
    media = uploaded.json()
    created = client.post(
        "/v1/jobs",
        headers=headers,
        json={"object_key": media["object_key"], "filename": "clip.mp4"},
    )
    assert created.status_code == 202
    foreign_key = new_object_key("user_other", "clip.mp4")
    storage.put(foreign_key, b"abc", "video/mp4")
    store.create(
        user_id="user_other",
        filename="clip.mp4",
        content_type="video/mp4",
        byte_size=3,
        object_key=foreign_key,
    )
    listed = client.get("/v1/jobs", headers=headers)
    assert listed.status_code == 200
    body = listed.json()
    assert [row["id"] for row in body] == [created.json()["id"]]
    assert body[0]["byte_size"] == len(b"video-bytes")
    assert body[0]["object_etag"]
    assert listed.headers["x-has-more"] == "false"


def test_list_jobs_pages_older_than_the_last_row(stack, monkeypatch: pytest.MonkeyPatch) -> None:
    client, store, _queue, _storage = stack
    ids = iter(
        (
            "job_00000000000a",
            "job_00000000000b",
            "job_00000000000c",
            "job_00000000000d",
        )
    )
    monkeypatch.setattr("secureai_shared.store._new_id", lambda: next(ids))
    moment = datetime(2026, 11, 1, 12, 0, tzinfo=timezone.utc)
    created: list[str] = []
    for name, when in (
        ("older.mp4", moment),
        ("tied.mp4", moment),
        ("newest.mp4", moment + timedelta(seconds=5)),
    ):
        job = store.create(
            user_id="user_dev",
            filename=name,
            content_type="video/mp4",
            byte_size=1,
            object_key=new_object_key("user_dev", name),
        )
        store._rows[job.id] = job.model_copy(update={"created_at": when})  # noqa: SLF001
        created.append(job.id)
    workspace = store.create(
        user_id="user_dev",
        filename="workspace.mp4",
        content_type="video/mp4",
        byte_size=1,
        object_key=new_object_key("user_dev", "workspace.mp4"),
        org_id="org_0123456789ab",
    )
    store._rows[workspace.id] = workspace.model_copy(  # noqa: SLF001
        update={"created_at": moment + timedelta(hours=1)}
    )
    headers = {"Authorization": "Bearer dev", "Origin": "http://localhost:3000"}
    first = client.get("/v1/jobs", headers=headers, params={"limit": 2})
    assert first.status_code == 200
    assert first.headers["x-has-more"] == "true"
    assert "x-has-more" in first.headers["access-control-expose-headers"].lower()
    body = first.json()
    assert [row["id"] for row in body] == [created[2], created[1]]
    assert workspace.id not in {row["id"] for row in body}

    second = client.get(
        "/v1/jobs",
        headers=headers,
        params={"limit": 2, "before": body[-1]["created_at"], "before_id": body[-1]["id"]},
    )
    assert second.status_code == 200
    assert second.headers["x-has-more"] == "false"
    assert [row["id"] for row in second.json()] == [created[0]]

    missing_id = client.get(
        "/v1/jobs",
        headers=headers,
        params={"before": "2026-11-01T12:00:00Z"},
    )
    assert missing_id.status_code == 400
    missing_time = client.get(
        "/v1/jobs",
        headers=headers,
        params={"before_id": created[0]},
    )
    assert missing_time.status_code == 400
    naive = client.get(
        "/v1/jobs",
        headers=headers,
        params={"before": "2026-11-01T12:00:00", "before_id": created[0]},
    )
    assert naive.status_code == 400
    malformed = client.get(
        "/v1/jobs",
        headers=headers,
        params={"before": "2026-11-01T12:00:00Z", "before_id": "not-a-job"},
    )
    assert malformed.status_code == 400
    oversized = client.get("/v1/jobs", headers=headers, params={"limit": 51})
    assert oversized.status_code == 422


def test_rate_limit_on_job_create(tmp_path: Path) -> None:
    settings = make_settings(tmp_path)
    store_queue_storage = _client(tmp_path, settings)
    client, _store, _queue, storage = store_queue_storage
    app_client = client
    # Rebuild with a tiny limiter while keeping the same store, queue, and files.
    from app.main import create_app as build

    limited = build(
        settings=settings,
        store=client.app.state.store,  # type: ignore[attr-defined]
        queue=client.app.state.queue,  # type: ignore[attr-defined]
        storage=storage,
        limiter=MemoryRateLimiter({"jobs": 1, "uploads": 10}, 60),
    )
    headers = {"Authorization": "Bearer dev"}
    with TestClient(limited) as api:
        first_key = new_object_key("user_dev", "clip.mp4")
        second_key = new_object_key("user_dev", "other.mp4")
        storage.put(first_key, b"one", "video/mp4")
        storage.put(second_key, b"two", "video/mp4")
        ok = api.post("/v1/jobs", headers=headers, json={"object_key": first_key, "filename": "clip.mp4"})
        blocked = api.post(
            "/v1/jobs",
            headers=headers,
            json={"object_key": second_key, "filename": "other.mp4"},
        )
    assert ok.status_code == 202
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "Too many requests"
    app_client.close()


def test_failed_enqueue_marks_the_row_failed(tmp_path: Path) -> None:
    class DownQueue(MemoryJobQueue):
        def publish(self, job_id: str) -> None:
            del job_id
            raise RuntimeError("redis down")

    client, store, _queue, storage = _client(tmp_path, make_settings(tmp_path))
    from app.main import create_app as build

    api_app = build(
        settings=make_settings(tmp_path),
        store=store,
        queue=DownQueue(),
        storage=storage,
    )
    key = new_object_key("user_dev", "clip.mp4")
    storage.put(key, b"video", "video/mp4")
    with TestClient(api_app) as api:
        response = api.post(
            "/v1/jobs",
            headers={"Authorization": "Bearer dev"},
            json={"object_key": key, "filename": "clip.mp4", "byte_size": 1},
        )
    assert response.status_code == 503
    assert response.json()["detail"] == UNQUEUED_FAILURE_DETAIL
    rows = list(store._rows.values())  # noqa: SLF001
    assert len(rows) == 1
    assert rows[0].status.value == "failed"
    assert rows[0].detail == UNQUEUED_FAILURE_DETAIL
    assert rows[0].attempt == 0
    assert store.count_started(user_id="user_dev", org_id=None, since=rows[0].created_at) == 0
    client.close()


def test_failed_enqueue_does_not_spend_the_monthly_quota(tmp_path: Path) -> None:
    class DownQueue(MemoryJobQueue):
        def publish(self, job_id: str) -> None:
            del job_id
            raise RuntimeError("redis down")

    settings = make_settings(tmp_path, quota_free=1, quota_mode="enforce")
    client, store, _queue, storage = _client(tmp_path, settings)
    from app.main import create_app as build

    api_app = build(settings=settings, store=store, queue=DownQueue(), storage=storage)
    key = new_object_key("user_dev", "clip.mp4")
    storage.put(key, b"video", "video/mp4")
    with TestClient(api_app) as api:
        failed = api.post(
            "/v1/jobs",
            headers={"Authorization": "Bearer dev"},
            json={"object_key": key, "filename": "clip.mp4"},
        )
        assert failed.status_code == 503
    client.close()

    again = build(
        settings=settings,
        store=store,
        queue=MemoryJobQueue(),
        storage=storage,
    )
    other = new_object_key("user_dev", "other.mp4")
    storage.put(other, b"video", "video/mp4")
    with TestClient(again) as api:
        created = api.post(
            "/v1/jobs",
            headers={"Authorization": "Bearer dev"},
            json={"object_key": other, "filename": "other.mp4"},
        )
    assert created.status_code == 202


def test_wildcard_cors_refuses_to_boot(tmp_path: Path) -> None:
    base = Settings(
        auth_mode="dev",
        clerk_issuer="",
        clerk_jwks_url="",
        clerk_authorized_parties=(),
        database_url="postgresql+psycopg://unused/unused",
        redis_url="",
        queue_backend="memory",
        queue_key="secureai:jobs",
        storage_backend="filesystem",
        media_root=str(tmp_path),
        s3_endpoint="",
        s3_bucket="",
        s3_access_key_id="",
        s3_secret_access_key="",
        s3_region="us-east-1",
        cors_origins=("*",),
        dev_subject="user_dev",
        max_upload_bytes=50_000_000,
    )
    try:
        create_app(settings=base, store=object(), queue=object(), storage=object())  # type: ignore[arg-type]
    except RuntimeError as exc:
        assert "CORS_ORIGINS" in str(exc)
    else:
        raise AssertionError("wildcard CORS should fail closed")
