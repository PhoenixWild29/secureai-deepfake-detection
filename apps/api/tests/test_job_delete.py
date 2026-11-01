"""DELETE /v1/jobs/{id} removes the video and the score without refunding quota."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from conftest import make_settings
from secureai_shared.attestation import AttestationRecord
from secureai_shared.billing import MemoryBillingStore
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.storage import FileSystemStorage, new_object_key
from secureai_shared.store import MemoryJobStore

AUTH = {"Authorization": "Bearer dev"}


def _upload(client: TestClient, storage: FileSystemStorage, headers: dict[str, str], name: str):
    key = new_object_key("user_dev", name)
    storage.put(key, b"video-bytes", "video/mp4")
    created = client.post(
        "/v1/jobs",
        headers=headers,
        json={"object_key": key, "filename": name, "content_type": "video/mp4"},
    )
    assert created.status_code == 202, created.text
    return created.json()["id"], key


def test_delete_removes_the_video_score_and_attestation_but_not_the_queue_id(stack) -> None:
    client, store, queue, storage = stack
    job_id, key = _upload(client, storage, AUTH, "clip.mp4")
    client.app.state.attestations.save(
        AttestationRecord(
            job_id=job_id,
            key_id="v1",
            algorithm="Ed25519",
            payload="{}",
            signature="abc",
            created_at=datetime.now(timezone.utc),
        )
    )
    assert storage.exists(key)

    removed = client.delete(f"/v1/jobs/{job_id}", headers=AUTH)
    assert removed.status_code == 204
    assert removed.content == b""
    assert not storage.exists(key)
    assert client.get(f"/v1/jobs/{job_id}", headers=AUTH).status_code == 404
    assert client.get(f"/v1/jobs/{job_id}/report", headers=AUTH).status_code == 404
    assert client.get(f"/v1/jobs/{job_id}/report.pdf", headers=AUTH).status_code == 404
    listed = client.get("/v1/jobs", headers=AUTH)
    assert listed.status_code == 200
    assert listed.json() == []
    assert client.app.state.attestations.get(job_id) is None
    again = client.delete(f"/v1/jobs/{job_id}", headers=AUTH)
    assert again.status_code == 404

    # The id can still be waiting. The worker pops it, finds no row, and acks.
    assert queue.consume() == job_id
    assert store.claim(job_id) is None

    assert client.delete("/v1/jobs/not-a-job", headers=AUTH).status_code == 404
    assert client.delete(f"/v1/jobs/{job_id}").status_code == 401


def test_delete_keeps_the_monthly_count(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, quota_free=1, quota_mode="enforce")
    storage = FileSystemStorage(tmp_path)
    client = TestClient(
        create_app(
            settings=settings,
            store=MemoryJobStore(),
            queue=MemoryJobQueue(),
            storage=storage,
            billing=MemoryBillingStore(),
        )
    )
    with client:
        job_id, _key = _upload(client, storage, AUTH, "one.mp4")
        assert client.delete(f"/v1/jobs/{job_id}", headers=AUTH).status_code == 204
        billing = client.get("/v1/billing", headers=AUTH)
        assert billing.status_code == 200
        assert billing.json()["jobs_used"] == 1
        key = new_object_key("user_dev", "two.mp4")
        storage.put(key, b"video-bytes", "video/mp4")
        blocked = client.post(
            "/v1/jobs",
            headers=AUTH,
            json={"object_key": key, "filename": "two.mp4", "content_type": "video/mp4"},
        )
        assert blocked.status_code == 402


def test_shared_object_is_erased_with_the_last_job(stack) -> None:
    client, _store, _queue, storage = stack
    key = new_object_key("user_dev", "clip.mp4")
    storage.put(key, b"video-bytes", "video/mp4")
    ids = []
    for name in ("one.mp4", "two.mp4"):
        created = client.post(
            "/v1/jobs",
            headers=AUTH,
            json={"object_key": key, "filename": name, "content_type": "video/mp4"},
        )
        assert created.status_code == 202, created.text
        ids.append(created.json()["id"])
    assert client.delete(f"/v1/jobs/{ids[0]}", headers=AUTH).status_code == 204
    assert storage.exists(key)
    assert client.get(f"/v1/jobs/{ids[1]}", headers=AUTH).status_code == 200
    assert client.delete(f"/v1/jobs/{ids[1]}", headers=AUTH).status_code == 204
    assert not storage.exists(key)


def test_processing_job_and_storage_errors_keep_the_file(stack) -> None:
    client, store, _queue, storage = stack
    job_id, key = _upload(client, storage, AUTH, "clip.mp4")
    assert store.claim(job_id) is not None
    busy = client.delete(f"/v1/jobs/{job_id}", headers=AUTH)
    assert busy.status_code == 409
    assert busy.json()["detail"] == "This job is still scoring. Try again when it finishes."
    assert storage.exists(key)
    assert client.get(f"/v1/jobs/{job_id}", headers=AUTH).status_code == 200

    store.release(job_id)

    def boom(_key: str) -> None:
        raise RuntimeError("disk")

    storage.delete = boom  # type: ignore[method-assign]
    failed = client.delete(f"/v1/jobs/{job_id}", headers=AUTH)
    assert failed.status_code == 500
    assert failed.json()["detail"] == "Could not delete the video"
    assert client.get(f"/v1/jobs/{job_id}", headers=AUTH).status_code == 200
    body = client.get(f"/v1/jobs/{job_id}", headers=AUTH).json()
    assert body["filename"] == "clip.mp4"
    assert body["status"] == "queued"


def test_other_user_cannot_delete_a_job(stack) -> None:
    client, store, _queue, storage = stack
    key = new_object_key("user_other", "clip.mp4")
    storage.put(key, b"abc", "video/mp4")
    job = store.create(
        user_id="user_other",
        filename="clip.mp4",
        content_type="video/mp4",
        byte_size=3,
        object_key=key,
    )
    missing = client.delete(f"/v1/jobs/{job.id}", headers=AUTH)
    assert missing.status_code == 404
    assert storage.exists(key)
    assert store.get_any(job.id) is not None


def test_workspace_member_cannot_delete_someone_elses_job(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, quota_mode="enforce", seat_limit_free=3)
    store = MemoryJobStore()
    billing = MemoryBillingStore()
    queue = MemoryJobQueue()
    storage = FileSystemStorage(tmp_path)
    owner = TestClient(
        create_app(settings=settings, store=store, queue=queue, storage=storage, billing=billing)
    )
    member = TestClient(
        create_app(
            settings=make_settings(tmp_path, dev_subject="user_member", quota_mode="enforce"),
            store=store,
            queue=queue,
            storage=storage,
            billing=billing,
        )
    )
    admin = TestClient(
        create_app(
            settings=make_settings(tmp_path, dev_subject="user_admin", quota_mode="enforce"),
            store=store,
            queue=queue,
            storage=storage,
            billing=billing,
        )
    )
    with owner, member, admin:
        created = owner.post("/v1/orgs", headers=AUTH, json={"name": "Studio"})
        assert created.status_code == 201
        org_id = created.json()["id"]
        assert (
            owner.post(
                f"/v1/orgs/{org_id}/members",
                headers=AUTH,
                json={"user_id": "user_member"},
            ).status_code
            == 201
        )
        assert (
            owner.post(
                f"/v1/orgs/{org_id}/members",
                headers=AUTH,
                json={"user_id": "user_admin"},
            ).status_code
            == 201
        )
        billing._members[org_id]["user_admin"] = "admin"  # noqa: SLF001
        org_headers = {**AUTH, "X-Org-Id": org_id}
        key = new_object_key("user_dev", "clip.mp4")
        storage.put(key, b"video-bytes", "video/mp4")
        uploaded = owner.post(
            "/v1/jobs",
            headers=org_headers,
            json={"object_key": key, "filename": "clip.mp4", "content_type": "video/mp4"},
        )
        assert uploaded.status_code == 202, uploaded.text
        job_id = uploaded.json()["id"]

        denied = member.delete(f"/v1/jobs/{job_id}", headers=org_headers)
        assert denied.status_code == 403
        assert storage.exists(key)
        assert member.get(f"/v1/jobs/{job_id}", headers=org_headers).status_code == 200

        allowed = admin.delete(f"/v1/jobs/{job_id}", headers=org_headers)
        assert allowed.status_code == 204
        assert not storage.exists(key)
        assert owner.get(f"/v1/jobs/{job_id}", headers=org_headers).status_code == 404

        member_key = new_object_key("user_member", "mine.mp4")
        storage.put(member_key, b"video-bytes", "video/mp4")
        mine = member.post(
            "/v1/jobs",
            headers=org_headers,
            json={"object_key": member_key, "filename": "mine.mp4", "content_type": "video/mp4"},
        )
        assert mine.status_code == 202, mine.text
        assert member.delete(f"/v1/jobs/{mine.json()['id']}", headers=org_headers).status_code == 204
        assert not storage.exists(member_key)
