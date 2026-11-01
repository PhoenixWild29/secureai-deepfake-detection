"""Register a workspace webhook and keep other organizations from reading it."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from conftest import make_settings
from secureai_shared.billing import MemoryBillingStore
from secureai_shared.models import JobStatus
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.storage import FileSystemStorage, new_object_key
from secureai_shared.store import MemoryJobStore
from secureai_shared.webhook_queue import MemoryWebhookQueue
from secureai_shared.webhooks import (
    SIGNATURE_HEADER,
    MemoryWebhookStore,
    deliver_once,
    schedule_terminal,
    signature_header,
)

AUTH = {"Authorization": "Bearer dev"}
SECRET = "whsec-test-signing-key"
URL = "https://customer.example/hooks/secureai"


def _clients(tmp_path: Path, subjects: list[str]):
    store = MemoryJobStore()
    billing = MemoryBillingStore()
    webhooks = MemoryWebhookStore()
    queue = MemoryJobQueue()
    webhook_queue = MemoryWebhookQueue()
    storage = FileSystemStorage(tmp_path)
    clients: list[TestClient] = []
    for subject in subjects:
        app = create_app(
            settings=make_settings(tmp_path, dev_subject=subject),
            store=store,
            queue=queue,
            storage=storage,
            billing=billing,
            webhooks=webhooks,
            webhook_queue=webhook_queue,
        )
        clients.append(TestClient(app))
    return clients, store, billing, webhooks, webhook_queue


def test_owner_registers_member_reads_and_outsiders_learn_nothing(tmp_path: Path) -> None:
    (owner, member, outsider), _store, billing, webhooks, _queue = _clients(
        tmp_path,
        ["user_dev", "user_member", "user_other"],
    )
    with owner, member, outsider:
        created = owner.post("/v1/orgs", headers=AUTH, json={"name": "Studio"})
        assert created.status_code == 201
        org_id = created.json()["id"]
        added = owner.post(
            f"/v1/orgs/{org_id}/members",
            headers=AUTH,
            json={"user_id": "user_member"},
        )
        assert added.status_code == 201
        with billing._lock:  # noqa: SLF001
            billing._members[org_id]["user_admin"] = "admin"

        missing = owner.get(f"/v1/orgs/{org_id}/webhook", headers=AUTH)
        assert missing.status_code == 200
        assert missing.json()["configured"] is False
        assert missing.json()["can_manage"] is True

        rejected = owner.put(
            f"/v1/orgs/{org_id}/webhook",
            headers=AUTH,
            json={"url": "http://customer.example/hooks", "secret": SECRET},
        )
        assert rejected.status_code == 400
        short = owner.put(
            f"/v1/orgs/{org_id}/webhook",
            headers=AUTH,
            json={"url": URL, "secret": "too-short"},
        )
        assert short.status_code == 400

        saved = owner.put(
            f"/v1/orgs/{org_id}/webhook",
            headers=AUTH,
            json={"url": URL, "secret": SECRET, "notify_failures": False},
        )
        assert saved.status_code == 200
        body = saved.json()
        assert body["url"] == URL
        assert body["secret_set"] is True
        assert body["notify_failures"] is False
        assert body["can_manage"] is True
        assert "secret" not in body
        assert SECRET not in saved.text
        assert webhooks.get_endpoint(org_id).secret == SECRET  # type: ignore[union-attr]

        kept = owner.put(
            f"/v1/orgs/{org_id}/webhook",
            headers=AUTH,
            json={"url": URL, "notify_failures": True},
        )
        assert kept.status_code == 200
        assert kept.json()["secret_set"] is True
        assert SECRET not in kept.text

        visible = member.get(f"/v1/orgs/{org_id}/webhook", headers=AUTH)
        assert visible.status_code == 200
        assert visible.json()["url"] == URL
        assert visible.json()["can_manage"] is False
        assert SECRET not in visible.text
        denied = member.put(
            f"/v1/orgs/{org_id}/webhook",
            headers=AUTH,
            json={"url": "https://other.example/hook"},
        )
        assert denied.status_code == 403
        assert "customer.example" not in denied.text

        admin = TestClient(
            create_app(
                settings=make_settings(tmp_path, dev_subject="user_admin"),
                store=owner.app.state.store,
                queue=owner.app.state.queue,
                storage=owner.app.state.storage,
                billing=billing,
                webhooks=webhooks,
                webhook_queue=owner.app.state.webhook_queue,
            )
        )
        with admin:
            changed = admin.put(
                f"/v1/orgs/{org_id}/webhook",
                headers=AUTH,
                json={"url": "https://customer.example/hooks/next", "secret": ""},
            )
            assert changed.status_code == 200
            assert changed.json()["secret_set"] is False
            assert changed.json()["url"].endswith("/next")

        hidden = outsider.get(f"/v1/orgs/{org_id}/webhook", headers=AUTH)
        assert hidden.status_code == 403
        assert "customer.example" not in hidden.text
        assert SECRET not in hidden.text
        hidden_put = outsider.put(
            f"/v1/orgs/{org_id}/webhook",
            headers=AUTH,
            json={"url": URL, "secret": SECRET},
        )
        assert hidden_put.status_code == 403
        assert "customer.example" not in hidden_put.text
        other_org = outsider.post("/v1/orgs", headers=AUTH, json={"name": "Elsewhere"})
        assert other_org.status_code == 201
        foreign = other_org.json()["id"]
        leaked = outsider.get(f"/v1/orgs/{org_id}/webhook/deliveries", headers=AUTH)
        assert leaked.status_code == 403
        own = owner.get(f"/v1/orgs/{foreign}/webhook", headers=AUTH)
        assert own.status_code == 403
        assert owner.get("/v1/orgs/not-an-org/webhook", headers=AUTH).status_code == 404
        assert owner.get(f"/v1/orgs/{org_id}/webhook", headers={}).status_code == 401

        removed = owner.delete(f"/v1/orgs/{org_id}/webhook", headers=AUTH)
        assert removed.status_code == 204
        assert member.delete(f"/v1/orgs/{org_id}/webhook", headers=AUTH).status_code == 403
        cleared = owner.get(f"/v1/orgs/{org_id}/webhook", headers=AUTH)
        assert cleared.json()["configured"] is False


def test_registered_secret_signs_and_failure_is_listed(tmp_path: Path) -> None:
    (owner,), store, _billing, _webhooks, webhook_queue = _clients(tmp_path, ["user_dev"])
    with owner:
        org_id = owner.post("/v1/orgs", headers=AUTH, json={"name": "Studio"}).json()["id"]
        saved = owner.put(
            f"/v1/orgs/{org_id}/webhook",
            headers=AUTH,
            json={"url": URL, "secret": SECRET, "notify_failures": True},
        )
        assert saved.status_code == 200
        job = store.create(
            user_id="user_dev",
            filename="clip.mp4",
            content_type="video/mp4",
            byte_size=4,
            object_key=new_object_key("user_dev", "clip.mp4"),
            org_id=org_id,
        )
        claimed = store.claim(job.id)
        assert claimed is not None
        finished = store.complete(job.id, prediction="real", confidence=0.25, attempt=claimed.attempt)
        assert finished is not None
        assert finished.status is JobStatus.completed
        when = finished.updated_at
        delivery_id = schedule_terminal(owner.app.state.webhooks, webhook_queue, finished, now=when)
        assert delivery_id is not None
        seen: dict[str, object] = {}

        def post(url: str, body: bytes, headers: dict[str, str], timeout: float) -> int:
            del timeout
            seen["url"] = url
            seen["body"] = body
            seen["headers"] = dict(headers)
            return 500

        assert (
            deliver_once(
                owner.app.state.webhooks,
                webhook_queue,
                post=post,
                timeout=2,
                max_attempts=1,
                now=when,
            )
            is True
        )
        headers = seen["headers"]
        body = seen["body"]
        assert isinstance(headers, dict)
        assert isinstance(body, bytes)
        timestamp = int(when.timestamp())
        assert headers[SIGNATURE_HEADER] == signature_header(SECRET, timestamp, body)
        payload = json.loads(body)
        assert payload["job_id"] == job.id
        assert payload["status"] == "completed"
        assert payload["prediction"] == "real"
        assert payload["confidence"] == 0.25
        assert payload["org_id"] == org_id
        assert "timestamp" in payload
        listed = owner.get(f"/v1/orgs/{org_id}/webhook/deliveries", headers=AUTH)
        assert listed.status_code == 200
        row = listed.json()[0]
        assert row["status"] == "failed"
        assert row["attempt"] == 1
        assert row["last_status_code"] == 500
        assert row["job_id"] == job.id
        assert SECRET not in listed.text
        summary = owner.get(f"/v1/orgs/{org_id}/webhook", headers=AUTH)
        assert summary.json()["last_delivery"]["status"] == "failed"
        assert SECRET not in summary.text
