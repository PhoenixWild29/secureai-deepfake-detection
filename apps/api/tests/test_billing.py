"""Quotas, workspaces, and Stripe webhooks. Stripe HTTP calls are replaced."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from conftest import make_settings
from secureai_shared.billing import MemoryBillingStore, PlanUpdate
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.storage import FileSystemStorage, new_object_key
from secureai_shared.store import MemoryJobStore

AUTH = {"Authorization": "Bearer dev"}
SECRET = "whsec_test_secret"


def _stack(tmp_path: Path, **overrides: object):
    settings = make_settings(tmp_path, **overrides)
    store = MemoryJobStore()
    billing = MemoryBillingStore()
    queue = MemoryJobQueue()
    storage = FileSystemStorage(tmp_path)
    app = create_app(
        settings=settings,
        store=store,
        queue=queue,
        storage=storage,
        billing=billing,
    )
    return TestClient(app), store, billing, storage


def _post_job(client: TestClient, storage: FileSystemStorage, user_id: str, headers: dict[str, str], name: str):
    key = new_object_key(user_id, name)
    storage.put(key, b"video-bytes", "video/mp4")
    return client.post(
        "/v1/jobs",
        headers=headers,
        json={"object_key": key, "filename": name, "content_type": "video/mp4"},
    )


def _sign(payload: bytes, secret: str = SECRET) -> str:
    timestamp = int(time.time())
    signed = f"{timestamp}.{payload.decode()}"
    digest = hmac.new(secret.encode(), signed.encode(), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def _event(event_id: str, event_type: str, obj: dict[str, object]) -> bytes:
    return json.dumps(
        {"id": event_id, "object": "event", "type": event_type, "data": {"object": obj}}
    ).encode()


def _post_event(client: TestClient, payload: bytes, secret: str = SECRET):
    return client.post(
        "/v1/billing/webhook",
        content=payload,
        headers={"Stripe-Signature": _sign(payload, secret), "Content-Type": "application/json"},
    )


def test_free_quota_is_402_and_pro_quota_is_403(tmp_path: Path) -> None:
    client, _store, billing, storage = _stack(tmp_path, quota_free=1, quota_pro=2, quota_mode="enforce")
    with client:
        first = _post_job(client, storage, "user_dev", AUTH, "one.mp4")
        second = _post_job(client, storage, "user_dev", AUTH, "two.mp4")
        assert first.status_code == 202
        assert second.status_code == 402
        assert "free trial" in second.json()["detail"]
        assert "Upgrade" in second.json()["detail"]

        billing.apply_stripe_event(
            "evt_grant",
            "customer.subscription.updated",
            PlanUpdate(user_id="user_dev", plan="pro", status="active"),
        )
        upgraded = _post_job(client, storage, "user_dev", AUTH, "three.mp4")
        blocked = _post_job(client, storage, "user_dev", AUTH, "four.mp4")
    assert upgraded.status_code == 202
    assert blocked.status_code == 403
    assert "Pro" in blocked.json()["detail"]


def test_unlimited_quota_allows_jobs_past_the_free_trial(tmp_path: Path) -> None:
    client, _store, _billing, storage = _stack(tmp_path, quota_free=1, quota_mode="unlimited")
    with client:
        first = _post_job(client, storage, "user_dev", AUTH, "one.mp4")
        second = _post_job(client, storage, "user_dev", AUTH, "two.mp4")
        view = client.get("/v1/billing", headers=AUTH)
    assert first.status_code == 202
    assert second.status_code == 202
    body = view.json()
    assert body["quota_mode"] == "unlimited"
    assert body["jobs_limit"] is None
    assert body["jobs_used"] == 2
    assert body["plan"] == "free"


def test_workspace_scopes_history_and_quota(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, quota_free=1, quota_mode="enforce", seat_limit_free=2)
    store = MemoryJobStore()
    billing = MemoryBillingStore()
    queue = MemoryJobQueue()
    storage = FileSystemStorage(tmp_path)
    owner = TestClient(
        create_app(settings=settings, store=store, queue=queue, storage=storage, billing=billing)
    )
    member_settings = make_settings(
        tmp_path,
        dev_subject="user_member",
        quota_free=1,
        quota_mode="enforce",
    )
    member = TestClient(
        create_app(
            settings=member_settings,
            store=store,
            queue=queue,
            storage=storage,
            billing=billing,
        )
    )
    outsider = TestClient(
        create_app(
            settings=make_settings(tmp_path, dev_subject="user_other", quota_mode="enforce"),
            store=store,
            queue=queue,
            storage=storage,
            billing=billing,
        )
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
        full = owner.post(
            f"/v1/orgs/{org_id}/members",
            headers=AUTH,
            json={"user_id": "user_third"},
        )
        assert full.status_code == 403

        org_headers = {**AUTH, "X-Org-Id": org_id}
        shared = _post_job(owner, storage, "user_dev", org_headers, "shared.mp4")
        assert shared.status_code == 202
        assert shared.json()["org_id"] == org_id
        again = _post_job(owner, storage, "user_dev", org_headers, "again.mp4")
        assert again.status_code == 402

        personal = _post_job(owner, storage, "user_dev", AUTH, "personal.mp4")
        assert personal.status_code == 202
        owner_personal = owner.get("/v1/jobs", headers=AUTH)
        assert [row["id"] for row in owner_personal.json()] == [personal.json()["id"]]

        member_list = member.get("/v1/jobs", headers={**AUTH, "X-Org-Id": org_id})
        assert member_list.status_code == 200
        assert [row["id"] for row in member_list.json()] == [shared.json()["id"]]
        hidden = member.get(f"/v1/jobs/{shared.json()['id']}", headers=AUTH)
        assert hidden.status_code == 404
        visible = member.get(f"/v1/jobs/{shared.json()['id']}", headers={**AUTH, "X-Org-Id": org_id})
        assert visible.status_code == 200

        denied = outsider.get("/v1/jobs", headers={**AUTH, "X-Org-Id": org_id})
        assert denied.status_code == 403
        billing_view = member.get("/v1/billing", headers={**AUTH, "X-Org-Id": org_id})
        assert billing_view.status_code == 200
        assert billing_view.json()["scope"] == "org"
        assert billing_view.json()["jobs_used"] == 1
        assert billing_view.json()["role"] == "member"


def test_checkout_and_portal_use_the_stripe_client(tmp_path: Path) -> None:
    client, _store, billing, _storage = _stack(
        tmp_path,
        stripe_secret_key="sk_test_example",
        stripe_webhook_secret=SECRET,
        stripe_price_pro="price_pro",
        stripe_price_team="price_team",
        public_app_url="http://localhost:3000",
    )
    with client:
        missing = client.post("/v1/billing/portal", headers=AUTH, json={})
        assert missing.status_code == 409

        stripe = client.app.state.stripe
        stripe.ensure_customer = lambda **_kwargs: "cus_test"  # type: ignore[method-assign]
        stripe.checkout_url = lambda **_kwargs: "https://checkout.stripe.test/c/pay"  # type: ignore[method-assign]
        stripe.portal_url = lambda **_kwargs: "https://billing.stripe.test/p/session"  # type: ignore[method-assign]

        created = client.post("/v1/orgs", headers=AUTH, json={"name": "Studio"})
        org_id = created.json()["id"]
        pro = client.post("/v1/billing/checkout", headers=AUTH, json={"plan": "pro"})
        assert pro.status_code == 200
        assert pro.json()["url"] == "https://checkout.stripe.test/c/pay"
        assert billing.user_account("user_dev").stripe_customer_id == "cus_test"

        team_missing = client.post("/v1/billing/checkout", headers=AUTH, json={"plan": "team"})
        assert team_missing.status_code == 400
        team = client.post(
            "/v1/billing/checkout",
            headers=AUTH,
            json={"plan": "team", "org_id": org_id},
        )
        assert team.status_code == 200
        assert billing.org_summary(org_id, user_id="user_dev").stripe_customer_id == "cus_test"

        portal = client.post("/v1/billing/portal", headers=AUTH, json={})
        assert portal.status_code == 200
        assert portal.json()["url"] == "https://billing.stripe.test/p/session"


def test_checkout_without_stripe_is_unavailable(tmp_path: Path) -> None:
    client, _store, _billing, _storage = _stack(tmp_path)
    with client:
        response = client.post("/v1/billing/checkout", headers=AUTH, json={"plan": "pro"})
    assert response.status_code == 503
    assert response.json()["detail"] == "Billing is not configured"


def test_webhook_happy_path_and_bad_signature(tmp_path: Path) -> None:
    client, _store, _billing, _storage = _stack(
        tmp_path,
        stripe_secret_key="sk_test_example",
        stripe_webhook_secret=SECRET,
        stripe_price_pro="price_pro",
        quota_pro=500,
        quota_free=10,
    )
    now = int(time.time())
    period_end = now + 10 * 24 * 3600
    checkout = _event(
        "evt_checkout",
        "checkout.session.completed",
        {
            "id": "cs_test",
            "object": "checkout.session",
            "customer": "cus_123",
            "subscription": "sub_123",
            "payment_status": "paid",
            "status": "complete",
            "metadata": {"user_id": "user_dev", "plan": "pro", "org_id": ""},
        },
    )
    paid = _event(
        "evt_paid",
        "invoice.paid",
        {
            "id": "in_123",
            "object": "invoice",
            "customer": "cus_123",
            "subscription": "sub_123",
            "lines": {"data": [{"period": {"start": now - 3600, "end": period_end}}]},
        },
    )
    failed = _event(
        "evt_failed",
        "invoice.payment_failed",
        {"id": "in_124", "object": "invoice", "customer": "cus_123", "subscription": "sub_123"},
    )
    deleted = _event(
        "evt_deleted",
        "customer.subscription.deleted",
        {
            "id": "sub_123",
            "object": "subscription",
            "customer": "cus_123",
            "status": "canceled",
            "metadata": {"user_id": "user_dev", "plan": "pro", "org_id": ""},
        },
    )
    with client:
        bad = client.post(
            "/v1/billing/webhook",
            content=checkout,
            headers={"Stripe-Signature": "t=1,v1=nope"},
        )
        assert bad.status_code == 400
        assert bad.json()["detail"] == "Invalid Stripe signature"
        anonymous = client.post("/v1/billing/webhook", content=checkout)
        assert anonymous.status_code == 400

        assert _post_event(client, checkout).status_code == 200
        active = client.get("/v1/billing", headers=AUTH).json()
        assert active["plan"] == "pro"
        assert active["subscription_status"] == "active"
        assert active["jobs_limit"] == 500

        assert _post_event(client, paid).json()["duplicate"] is False
        period = client.get("/v1/billing", headers=AUTH).json()
        assert period["plan"] == "pro"
        expected = datetime.fromtimestamp(period_end, timezone.utc).isoformat()
        assert period["period_end"].startswith(expected[:19])

        assert _post_event(client, failed).status_code == 200
        past_due = client.get("/v1/billing", headers=AUTH).json()
        assert past_due["plan"] == "pro"
        assert past_due["subscription_status"] == "past_due"

        assert _post_event(client, deleted).status_code == 200
        canceled = client.get("/v1/billing", headers=AUTH).json()
        assert canceled["plan"] == "free"
        assert canceled["subscription_status"] == "canceled"
        assert canceled["jobs_limit"] == 10

        replay = _event(
            "evt_deleted",
            "checkout.session.completed",
            {
                "id": "cs_other",
                "customer": "cus_123",
                "payment_status": "paid",
                "metadata": {"user_id": "user_dev", "plan": "pro", "org_id": ""},
            },
        )
        duplicate = _post_event(client, replay)
        assert duplicate.json()["duplicate"] is True
        assert client.get("/v1/billing", headers=AUTH).json()["plan"] == "free"


def test_dev_without_stripe_logs_an_unlimited_quota_warning(tmp_path: Path, caplog) -> None:
    caplog.set_level(logging.WARNING, logger="secureai.api")
    settings = make_settings(tmp_path, quota_mode="unlimited", stripe_secret_key="")
    create_app(
        settings=settings,
        store=MemoryJobStore(),
        queue=MemoryJobQueue(),
        storage=FileSystemStorage(tmp_path),
        billing=MemoryBillingStore(),
    )
    assert "quotas are unlimited" in caplog.text


def test_cors_allows_the_org_header(tmp_path: Path) -> None:
    client, _store, _billing, _storage = _stack(tmp_path)
    with client:
        response = client.options(
            "/v1/billing",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,x-org-id",
            },
        )
    assert response.status_code == 200
    allowed = response.headers.get("access-control-allow-headers", "").lower()
    assert "x-org-id" in allowed
