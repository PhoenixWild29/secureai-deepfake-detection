"""Batch create and JSON report export. Billing webhooks are not exercised."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from conftest import make_settings
from secureai_shared.billing import MemoryBillingStore, PlanUpdate
from secureai_shared.limits import MemoryRateLimiter
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.report import dump_report_detail
from secureai_shared.storage import FileSystemStorage, new_object_key
from secureai_shared.store import UNQUEUED_FAILURE_DETAIL, MemoryJobStore

AUTH = {"Authorization": "Bearer dev"}


def _item(storage: FileSystemStorage, user_id: str, name: str) -> dict[str, str]:
    key = new_object_key(user_id, name)
    storage.put(key, b"video-bytes", "video/mp4")
    return {"object_key": key, "filename": name, "content_type": "video/mp4"}


def test_batch_queues_each_object(stack) -> None:
    client, _store, queue, storage = stack
    items = [_item(storage, "user_dev", "one.mp4"), _item(storage, "user_dev", "two.mp4")]
    created = client.post("/v1/jobs/batch", headers=AUTH, json={"items": items})
    assert created.status_code == 202
    jobs = created.json()["jobs"]
    assert [job["filename"] for job in jobs] == ["one.mp4", "two.mp4"]
    assert [job["status"] for job in jobs] == ["queued", "queued"]
    assert jobs[0]["user_id"] == "user_dev"
    assert queue.consume() == jobs[0]["id"]
    assert queue.consume() == jobs[1]["id"]
    assert queue.consume() is None
    anonymous = client.post("/v1/jobs/batch", json={"items": items})
    assert anonymous.status_code == 401


def test_batch_over_free_quota_inserts_nothing(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, quota_free=1, quota_mode="enforce")
    store = MemoryJobStore()
    queue = MemoryJobQueue()
    storage = FileSystemStorage(tmp_path)
    client = TestClient(create_app(settings=settings, store=store, queue=queue, storage=storage))
    items = [_item(storage, "user_dev", "one.mp4"), _item(storage, "user_dev", "two.mp4")]
    with client:
        blocked = client.post("/v1/jobs/batch", headers=AUTH, json={"items": items})
    assert blocked.status_code == 402
    assert "free trial" in blocked.json()["detail"]
    assert "Upgrade" in blocked.json()["detail"]
    assert store._rows == {}  # noqa: SLF001
    assert queue.consume() is None


def test_batch_over_pro_quota_is_403(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, quota_pro=2, quota_mode="enforce")
    store = MemoryJobStore()
    billing = MemoryBillingStore()
    queue = MemoryJobQueue()
    storage = FileSystemStorage(tmp_path)
    billing.apply_stripe_event(
        "evt_grant",
        "customer.subscription.updated",
        PlanUpdate(user_id="user_dev", plan="pro", status="active"),
    )
    client = TestClient(
        create_app(
            settings=settings,
            store=store,
            queue=queue,
            storage=storage,
            billing=billing,
        )
    )
    items = [
        _item(storage, "user_dev", "one.mp4"),
        _item(storage, "user_dev", "two.mp4"),
        _item(storage, "user_dev", "three.mp4"),
    ]
    with client:
        blocked = client.post("/v1/jobs/batch", headers=AUTH, json={"items": items})
    assert blocked.status_code == 403
    assert "Pro" in blocked.json()["detail"]
    assert store._rows == {}  # noqa: SLF001


def test_batch_rejects_a_bad_item_without_inserting(stack) -> None:
    client, store, queue, storage = stack
    good = _item(storage, "user_dev", "one.mp4")
    foreign = {
        "object_key": new_object_key("someone_else", "two.mp4"),
        "filename": "two.mp4",
    }
    duplicate = client.post(
        "/v1/jobs/batch",
        headers=AUTH,
        json={"items": [good, good]},
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Duplicate object key"
    missing = client.post(
        "/v1/jobs/batch",
        headers=AUTH,
        json={"items": [good, foreign]},
    )
    assert missing.status_code == 400
    assert store._rows == {}  # noqa: SLF001
    assert queue.consume() is None


def test_batch_publish_failure_returns_ids_already_queued(tmp_path: Path) -> None:
    class FailSecond(MemoryJobQueue):
        """Reject every publish of the second distinct id. Retries stay down."""

        def __init__(self) -> None:
            super().__init__()
            self.seen: list[str] = []

        def publish(self, job_id: str) -> None:
            if job_id not in self.seen:
                self.seen.append(job_id)
            if len(self.seen) >= 2 and job_id == self.seen[1]:
                raise RuntimeError("redis down")
            super().publish(job_id)

    settings = make_settings(tmp_path, quota_mode="unlimited")
    store = MemoryJobStore()
    queue = FailSecond()
    storage = FileSystemStorage(tmp_path)
    items = [
        _item(storage, "user_dev", "one.mp4"),
        _item(storage, "user_dev", "two.mp4"),
        _item(storage, "user_dev", "three.mp4"),
    ]
    with TestClient(
        create_app(settings=settings, store=store, queue=queue, storage=storage)
    ) as client:
        created = client.post("/v1/jobs/batch", headers=AUTH, json={"items": items})
    assert created.status_code == 202
    jobs = created.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["filename"] == "one.mp4"
    assert jobs[0]["status"] == "queued"
    assert queue.consume() == jobs[0]["id"]
    assert queue.consume() is None
    rows = list(store._rows.values())  # noqa: SLF001
    failed = [row for row in rows if row.id != jobs[0]["id"]]
    assert len(failed) == 2
    assert {row.status.value for row in failed} == {"failed"}
    assert {row.detail for row in failed} == {UNQUEUED_FAILURE_DETAIL}


def test_invalid_batch_does_not_spend_the_rate_limit(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, quota_mode="unlimited")
    storage = FileSystemStorage(tmp_path)
    app = create_app(
        settings=settings,
        store=MemoryJobStore(),
        queue=MemoryJobQueue(),
        storage=storage,
        limiter=MemoryRateLimiter({"jobs": 2, "uploads": 10}, 60),
    )
    foreign = {
        "object_key": new_object_key("someone_else", "nope.mp4"),
        "filename": "nope.mp4",
    }
    valid = [
        _item(storage, "user_dev", "one.mp4"),
        _item(storage, "user_dev", "two.mp4"),
    ]
    with TestClient(app) as client:
        rejected = client.post(
            "/v1/jobs/batch",
            headers=AUTH,
            json={"items": [foreign, foreign]},
        )
        assert rejected.status_code == 400
        created = client.post("/v1/jobs/batch", headers=AUTH, json={"items": valid})
    assert created.status_code == 202
    assert len(created.json()["jobs"]) == 2


def test_batch_rate_limit_matches_single_creates(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, quota_mode="unlimited")
    storage = FileSystemStorage(tmp_path)
    app = create_app(
        settings=settings,
        store=MemoryJobStore(),
        queue=MemoryJobQueue(),
        storage=storage,
        limiter=MemoryRateLimiter({"jobs": 2, "uploads": 10}, 60),
    )
    items = [
        _item(storage, "user_dev", "one.mp4"),
        _item(storage, "user_dev", "two.mp4"),
        _item(storage, "user_dev", "three.mp4"),
    ]
    with TestClient(app) as client:
        blocked = client.post("/v1/jobs/batch", headers=AUTH, json={"items": items})
    assert blocked.status_code == 429
    assert blocked.json()["detail"] == "Too many requests"
    assert app.state.store._rows == {}  # noqa: SLF001


def test_batch_honors_org_header(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, quota_free=2, quota_mode="enforce")
    store = MemoryJobStore()
    queue = MemoryJobQueue()
    storage = FileSystemStorage(tmp_path)
    client = TestClient(create_app(settings=settings, store=store, queue=queue, storage=storage))
    items = [_item(storage, "user_dev", "one.mp4"), _item(storage, "user_dev", "two.mp4")]
    with client:
        org = client.post("/v1/orgs", headers=AUTH, json={"name": "Studio"})
        assert org.status_code == 201
        org_id = org.json()["id"]
        created = client.post(
            "/v1/jobs/batch",
            headers={**AUTH, "X-Org-Id": org_id},
            json={"items": items},
        )
        assert created.status_code == 202
        assert [job["org_id"] for job in created.json()["jobs"]] == [org_id, org_id]
        extra = _item(storage, "user_dev", "three.mp4")
        blocked = client.post(
            "/v1/jobs/batch",
            headers={**AUTH, "X-Org-Id": org_id},
            json={"items": [extra]},
        )
    assert blocked.status_code == 402
    assert "Upgrade" in blocked.json()["detail"]


def test_report_json_for_a_completed_job(stack) -> None:
    client, store, _queue, storage = stack
    item = _item(storage, "user_dev", "clip.mp4")
    created = client.post("/v1/jobs", headers=AUTH, json=item)
    assert created.status_code == 202
    job_id = created.json()["id"]
    waiting = client.get(f"/v1/jobs/{job_id}/report", headers=AUTH)
    assert waiting.status_code == 409

    claimed = store.claim(job_id)
    assert claimed is not None
    detail = dump_report_detail(
        "cpu-multisignal-v1",
        {"texture": 0.2, "motion": 0.1, "temporal": 0.3, "region": 0.0},
    )
    finished = store.complete(job_id, prediction="real", confidence=0.84, detail=detail)
    assert finished is not None

    exported = client.get(f"/v1/jobs/{job_id}/report", headers=AUTH)
    assert exported.status_code == 200
    assert exported.headers["content-disposition"] == f'attachment; filename="{job_id}.json"'
    body = exported.json()
    assert body["job_id"] == job_id
    assert body["prediction"] == "real"
    assert body["model"] == "cpu-multisignal-v1"
    assert body["signals"]["texture"] == 0.2
    assert body["pdf_available"] is False
    assert "not a trained deepfake classifier" in body["limitations"]

    hidden = client.get(f"/v1/jobs/{job_id}/report")
    assert hidden.status_code == 401
    outsider = TestClient(
        create_app(
            settings=make_settings(storage.root, dev_subject="user_other"),
            store=store,
            queue=MemoryJobQueue(),
            storage=storage,
        )
    )
    with outsider:
        forbidden = outsider.get(f"/v1/jobs/{job_id}/report", headers=AUTH)
    assert forbidden.status_code == 404
