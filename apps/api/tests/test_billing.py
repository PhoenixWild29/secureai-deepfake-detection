"""Quotas, workspaces, and Stripe webhooks. Stripe HTTP calls are replaced."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.stripe_client import StartedCheckout
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


def _event(
    event_id: str,
    event_type: str,
    obj: dict[str, object],
    *,
    created: int | None = None,
) -> bytes:
    body: dict[str, object] = {
        "id": event_id,
        "object": "event",
        "type": event_type,
        "data": {"object": obj},
    }
    if created is not None:
        body["created"] = created
    return json.dumps(body).encode()


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
        stripe.checkout_url = lambda **_kwargs: StartedCheckout(  # type: ignore[method-assign]
            url="https://checkout.stripe.test/c/pay",
            session_id="cs_test_mock",
        )
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
            "metadata": {"user_id": "user_dev", "plan": "team", "org_id": ""},
            "line_items": {"data": [{"price": {"id": "price_pro"}}]},
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


def test_late_update_after_delete_does_not_restore_the_plan(tmp_path: Path) -> None:
    client, _store, billing, _storage = _stack(
        tmp_path,
        stripe_secret_key="sk_test_example",
        stripe_webhook_secret=SECRET,
        stripe_price_pro="price_pro",
    )
    checkout = _event(
        "evt_checkout_order",
        "checkout.session.completed",
        {
            "customer": "cus_order",
            "subscription": "sub_old",
            "payment_status": "paid",
            "metadata": {"user_id": "user_dev", "plan": "team", "org_id": ""},
            "line_items": {"data": [{"price": {"id": "price_pro"}}]},
        },
        created=100,
    )
    deleted = _event(
        "evt_deleted_order",
        "customer.subscription.deleted",
        {
            "id": "sub_old",
            "customer": "cus_order",
            "status": "canceled",
            "metadata": {"user_id": "user_dev", "plan": "pro", "org_id": ""},
        },
        created=300,
    )
    late = _event(
        "evt_late_update",
        "customer.subscription.updated",
        {
            "id": "sub_old",
            "customer": "cus_order",
            "status": "active",
            "metadata": {"user_id": "user_dev", "plan": "pro", "org_id": ""},
            "items": {"data": [{"price": {"id": "price_pro"}}]},
        },
        created=200,
    )
    with client:
        assert _post_event(client, checkout).status_code == 200
        assert _post_event(client, deleted).status_code == 200
        assert client.get("/v1/billing", headers=AUTH).json()["plan"] == "free"
        assert _post_event(client, late).json()["duplicate"] is False
        body = client.get("/v1/billing", headers=AUTH).json()
    assert body["plan"] == "free"
    assert body["subscription_status"] == "canceled"
    assert billing.user_account("user_dev").stripe_subscription_id == "sub_old"


def test_old_subscription_delete_after_replacement_keeps_the_new_plan(tmp_path: Path) -> None:
    client, _store, billing, _storage = _stack(
        tmp_path,
        stripe_secret_key="sk_test_example",
        stripe_webhook_secret=SECRET,
        stripe_price_pro="price_pro",
    )

    def checkout(event_id: str, subscription_id: str, created: int) -> bytes:
        return _event(
            event_id,
            "checkout.session.completed",
            {
                "customer": "cus_replace",
                "subscription": subscription_id,
                "payment_status": "paid",
                "metadata": {"user_id": "user_dev", "plan": "team", "org_id": ""},
                "line_items": {"data": [{"price": {"id": "price_pro"}}]},
            },
            created=created,
        )

    old_delete = _event(
        "evt_old_delete",
        "customer.subscription.deleted",
        {
            "id": "sub_old",
            "customer": "cus_replace",
            "status": "canceled",
            "metadata": {"user_id": "user_dev", "plan": "pro", "org_id": ""},
        },
        created=400,
    )
    old_invoice = _event(
        "evt_old_invoice",
        "invoice.payment_failed",
        {
            "customer": "cus_replace",
            "subscription": "sub_old",
        },
        created=500,
    )
    with client:
        assert _post_event(client, checkout("evt_old_checkout", "sub_old", 100)).status_code == 200
        assert _post_event(client, checkout("evt_new_checkout", "sub_new", 200)).status_code == 200
        assert _post_event(client, old_delete).status_code == 200
        assert _post_event(client, old_invoice).status_code == 200
        body = client.get("/v1/billing", headers=AUTH).json()
    assert body["plan"] == "pro"
    assert body["subscription_status"] == "active"
    assert billing.user_account("user_dev").stripe_subscription_id == "sub_new"


def test_checkout_refuses_an_active_subscription(tmp_path: Path) -> None:
    client, _store, billing, _storage = _stack(
        tmp_path,
        stripe_secret_key="sk_test_example",
        stripe_webhook_secret=SECRET,
        stripe_price_pro="price_pro",
        stripe_price_team="price_team",
    )
    with client:
        stripe = client.app.state.stripe
        stripe.ensure_customer = lambda **_kwargs: "cus_test"  # type: ignore[method-assign]

        def forbid_checkout(**_kwargs: object) -> str:
            raise AssertionError("checkout must not create a second subscription")

        stripe.checkout_url = forbid_checkout  # type: ignore[method-assign]
        billing.apply_stripe_event(
            "evt_active",
            "customer.subscription.updated",
            PlanUpdate(
                user_id="user_dev",
                plan="pro",
                status="active",
                subscription_id="sub_live",
                event_created=10,
            ),
        )
        refused = client.post("/v1/billing/checkout", headers=AUTH, json={"plan": "pro"})
        assert refused.status_code == 409
        assert "billing portal" in refused.json()["detail"]

        billing.apply_stripe_event(
            "evt_past_due",
            "invoice.payment_failed",
            PlanUpdate(
                user_id="user_dev",
                status="past_due",
                subscription_id="sub_live",
                event_created=20,
            ),
        )
        past_due = client.post("/v1/billing/checkout", headers=AUTH, json={"plan": "pro"})
        assert past_due.status_code == 409

        created = client.post("/v1/orgs", headers=AUTH, json={"name": "Studio"})
        org_id = created.json()["id"]
        billing.apply_stripe_event(
            "evt_team",
            "checkout.session.completed",
            PlanUpdate(
                org_id=org_id,
                plan="team",
                status="trialing",
                subscription_id="sub_team",
                event_created=30,
                replaces_subscription=True,
            ),
        )
        team = client.post(
            "/v1/billing/checkout",
            headers=AUTH,
            json={"plan": "team", "org_id": org_id},
        )
        assert team.status_code == 409

        billing.apply_stripe_event(
            "evt_cancel",
            "customer.subscription.deleted",
            PlanUpdate(
                user_id="user_dev",
                plan="free",
                status="canceled",
                subscription_id="sub_live",
                event_created=40,
            ),
        )
        stripe.checkout_url = lambda **_kwargs: StartedCheckout(  # type: ignore[method-assign]
            url="https://checkout.stripe.test/c/pay",
            session_id="cs_test_mock",
        )
        allowed = client.post("/v1/billing/checkout", headers=AUTH, json={"plan": "pro"})
        assert allowed.status_code == 200
        assert allowed.json()["url"] == "https://checkout.stripe.test/c/pay"


def test_late_invoice_keeps_a_terminal_status_and_checkout_can_open(tmp_path: Path) -> None:
    """subscription.deleted, then a newer invoice, must not block resubscribe."""

    client, _store, billing, _storage = _stack(
        tmp_path,
        stripe_secret_key="sk_test_example",
        stripe_webhook_secret=SECRET,
        stripe_price_pro="price_pro",
    )

    def invoice(event_id: str, event_type: str, created: int) -> bytes:
        return _event(
            event_id,
            event_type,
            {
                "customer": "cus_terminal",
                "subscription": "sub_terminal",
                "metadata": {"user_id": "user_dev", "plan": "pro", "org_id": ""},
            },
            created=created,
        )

    checkout = _event(
        "evt_terminal_checkout",
        "checkout.session.completed",
        {
            "customer": "cus_terminal",
            "subscription": "sub_terminal",
            "payment_status": "paid",
            "metadata": {"user_id": "user_dev", "plan": "team", "org_id": ""},
            "line_items": {"data": [{"price": {"id": "price_pro"}}]},
        },
        created=100,
    )
    deleted = _event(
        "evt_terminal_deleted",
        "customer.subscription.deleted",
        {
            "id": "sub_terminal",
            "customer": "cus_terminal",
            "status": "canceled",
            "metadata": {"user_id": "user_dev", "plan": "pro", "org_id": ""},
        },
        created=200,
    )
    with client:
        stripe = client.app.state.stripe
        stripe.ensure_customer = lambda **_kwargs: "cus_terminal"  # type: ignore[method-assign]
        stripe.checkout_url = lambda **_kwargs: StartedCheckout(  # type: ignore[method-assign]
            url="https://checkout.stripe.test/c/pay",
            session_id="cs_resubscribe",
        )
        assert _post_event(client, checkout).status_code == 200
        assert client.get("/v1/billing", headers=AUTH).json()["plan"] == "pro"
        assert _post_event(client, deleted).status_code == 200
        assert _post_event(client, invoice("evt_late_paid", "invoice.paid", 300)).status_code == 200
        assert _post_event(client, invoice("evt_late_failed", "invoice.payment_failed", 400)).status_code == 200
        canceled = client.get("/v1/billing", headers=AUTH).json()
        assert canceled["plan"] == "free"
        assert canceled["subscription_status"] == "canceled"
        opened = client.post("/v1/billing/checkout", headers=AUTH, json={"plan": "pro"})
        assert opened.status_code == 200
        assert opened.json()["url"] == "https://checkout.stripe.test/c/pay"

        unpaid = _event(
            "evt_mark_unpaid",
            "customer.subscription.updated",
            {
                "id": "sub_terminal",
                "customer": "cus_terminal",
                "status": "unpaid",
                "metadata": {"user_id": "user_dev", "plan": "pro", "org_id": ""},
                "items": {"data": [{"price": {"id": "price_pro"}}]},
            },
            created=500,
        )
        assert _post_event(client, unpaid).status_code == 200
        assert _post_event(client, invoice("evt_unpaid_paid", "invoice.paid", 600)).status_code == 200
        assert _post_event(client, invoice("evt_unpaid_failed", "invoice.payment_failed", 700)).status_code == 200
        body = client.get("/v1/billing", headers=AUTH).json()
        assert body["subscription_status"] == "unpaid"
        assert body["plan"] == "free"
        again = client.post("/v1/billing/checkout", headers=AUTH, json={"plan": "pro"})
        assert again.status_code == 200
    assert billing.user_account("user_dev").subscription_status == "unpaid"


def test_checkout_without_a_price_uses_the_recorded_plan_not_metadata(tmp_path: Path) -> None:
    client, _store, billing, _storage = _stack(
        tmp_path,
        stripe_secret_key="sk_test_example",
        stripe_webhook_secret=SECRET,
        stripe_price_pro="price_pro",
        stripe_price_team="price_team",
    )
    billing.remember_checkout(session_id="cs_recorded", plan="pro", price_id="price_pro")
    recorded = _event(
        "evt_recorded_checkout",
        "checkout.session.completed",
        {
            "id": "cs_recorded",
            "customer": "cus_recorded",
            "subscription": "sub_recorded",
            "payment_status": "paid",
            "metadata": {"user_id": "user_dev", "plan": "team", "org_id": ""},
        },
        created=100,
    )
    unknown = _event(
        "evt_unknown_checkout_price",
        "checkout.session.completed",
        {
            "id": "cs_other",
            "customer": "cus_recorded",
            "subscription": "sub_other",
            "payment_status": "paid",
            "metadata": {"user_id": "user_dev", "plan": "team", "org_id": ""},
            "line_items": {"data": [{"price": {"id": "price_not_configured"}}]},
        },
        created=200,
    )
    with client:
        assert _post_event(client, recorded).status_code == 200
        body = client.get("/v1/billing", headers=AUTH).json()
        assert body["plan"] == "pro"
        assert body["subscription_status"] == "active"
        assert _post_event(client, unknown).status_code == 200
        # Unknown price must not fall back to metadata.plan or the earlier intent.
        stayed = client.get("/v1/billing", headers=AUTH).json()
    assert stayed["plan"] == "pro"
    assert stayed["subscription_status"] == "active"
    assert billing.user_account("user_dev").stripe_subscription_id == "sub_recorded"


def test_unknown_price_does_not_upgrade_from_metadata(tmp_path: Path) -> None:
    client, _store, _billing, _storage = _stack(
        tmp_path,
        stripe_secret_key="sk_test_example",
        stripe_webhook_secret=SECRET,
        stripe_price_pro="price_pro",
        stripe_price_team="price_team",
    )
    unknown = _event(
        "evt_unknown_price",
        "customer.subscription.updated",
        {
            "id": "sub_unknown",
            "customer": "cus_unknown",
            "status": "active",
            "metadata": {"user_id": "user_dev", "plan": "team", "org_id": ""},
            "items": {"data": [{"price": {"id": "price_not_configured"}}]},
        },
        created=100,
    )
    with client:
        assert _post_event(client, unknown).status_code == 200
        body = client.get("/v1/billing", headers=AUTH).json()
    assert body["plan"] == "free"
    assert body["subscription_status"] is None


def test_team_downgrade_clamps_seats_to_the_free_limit(tmp_path: Path) -> None:
    client, _store, _billing, _storage = _stack(
        tmp_path,
        stripe_secret_key="sk_test_example",
        stripe_webhook_secret=SECRET,
        stripe_price_team="price_team",
        seat_limit_free=2,
        seat_limit_team=4,
        quota_mode="enforce",
    )
    with client:
        created = client.post("/v1/orgs", headers=AUTH, json={"name": "Studio"})
        org_id = created.json()["id"]
        checkout = _event(
            "evt_team_checkout",
            "checkout.session.completed",
            {
                "customer": "cus_team",
                "subscription": "sub_team",
                "payment_status": "paid",
                "metadata": {"user_id": "user_dev", "org_id": org_id, "plan": "pro"},
                "line_items": {"data": [{"price": {"id": "price_team"}}]},
            },
            created=100,
        )
        assert _post_event(client, checkout).status_code == 200
        for user_id in ("user_a", "user_b", "user_c"):
            added = client.post(
                f"/v1/orgs/{org_id}/members",
                headers=AUTH,
                json={"user_id": user_id},
            )
            assert added.status_code == 201
        deleted = _event(
            "evt_team_deleted",
            "customer.subscription.deleted",
            {
                "id": "sub_team",
                "customer": "cus_team",
                "status": "canceled",
                "metadata": {"user_id": "user_dev", "org_id": org_id, "plan": "team"},
            },
            created=200,
        )
        assert _post_event(client, deleted).status_code == 200
        view = client.get("/v1/billing", headers={**AUTH, "X-Org-Id": org_id}).json()
        assert view["plan"] == "free"
        assert view["subscription_status"] == "canceled"
        assert view["seats_used"] == 2
        assert view["seats_limit"] == 2
        member_ids = {row["user_id"] for row in view["members"]}
        assert member_ids == {"user_dev", "user_a"}
        # Hard-deleted, not hidden. A later Team upgrade does not restore them.
        assert _billing.membership(org_id, "user_b") is None
        assert _billing.membership(org_id, "user_c") is None
        assert _billing.list_orgs("user_b") == []
        upgraded = _event(
            "evt_team_again",
            "customer.subscription.updated",
            {
                "id": "sub_team",
                "customer": "cus_team",
                "status": "active",
                "metadata": {"user_id": "user_dev", "org_id": org_id, "plan": "free"},
                "items": {"data": [{"price": {"id": "price_team"}}]},
            },
            created=300,
        )
        assert _post_event(client, upgraded).status_code == 200
        again = client.get("/v1/billing", headers={**AUTH, "X-Org-Id": org_id}).json()
        assert again["plan"] == "team"
        assert {row["user_id"] for row in again["members"]} == {"user_dev", "user_a"}
        restored = client.post(
            f"/v1/orgs/{org_id}/members",
            headers=AUTH,
            json={"user_id": "user_c"},
        )
        assert restored.status_code == 201


def test_concurrent_quota_check_and_insert_do_not_overlap(tmp_path: Path) -> None:
    import threading
    import time

    from fastapi import HTTPException

    from app.quota import accept_job

    class SlowStore(MemoryJobStore):
        def __init__(self) -> None:
            super().__init__()
            self.overlap = 0
            self.max_overlap = 0
            self._gate = threading.Lock()

        def count_started(self, *, user_id: str, org_id: str | None, since: object) -> int:
            with self._gate:
                self.overlap += 1
                self.max_overlap = max(self.max_overlap, self.overlap)
            try:
                time.sleep(0.05)
                return super().count_started(user_id=user_id, org_id=org_id, since=since)  # type: ignore[arg-type]
            finally:
                with self._gate:
                    self.overlap -= 1

    settings = make_settings(tmp_path, quota_free=1, quota_mode="enforce")
    store = SlowStore()
    billing = MemoryBillingStore()
    ok: list[str] = []
    blocked: list[int] = []
    errors: list[BaseException] = []

    def once(name: str) -> None:
        try:
            job = accept_job(
                settings=settings,
                store=store,
                billing=billing,
                user_id="user_dev",
                org_id=None,
                filename=name,
                content_type="video/mp4",
                byte_size=4,
                object_key=new_object_key("user_dev", name),
                object_etag="abc",
            )
            ok.append(job.id)
        except HTTPException as exc:
            blocked.append(exc.status_code)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=once, args=(f"{name}.mp4",)) for name in ("one", "two")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert store.max_overlap == 1
    assert len(ok) == 1
    assert blocked == [402]


def test_postgres_row_lock_stops_a_concurrent_quota_overshoot(tmp_path: Path) -> None:
    """Two Postgres transactions cannot both pass a one-job cap."""

    import threading

    from app.quota import accept_job
    from secureai_shared.billing import PostgresBillingStore
    from secureai_shared.db import Base
    from secureai_shared.store import PostgresJobStore

    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://secureai:secureai@127.0.0.1:5432/secureai",
    )
    try:
        probe = PostgresJobStore(url)
        with probe.engine.connect() as connection:
            connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS secureai_quota_test")
            connection.commit()
        probe.engine.dispose()
    except Exception as exc:
        if os.environ.get("REQUIRE_SERVICES") == "1":
            pytest.fail(f"postgres unavailable: {exc}")
        pytest.skip(f"postgres unavailable: {exc}")

    schema_url = url + ("&" if "?" in url else "?") + "options=-csearch_path%3Dsecureai_quota_test"

    class SlowPostgres(PostgresJobStore):
        def __init__(self, database_url: str) -> None:
            super().__init__(database_url)
            self.overlap = 0
            self.max_overlap = 0
            self._gate = threading.Lock()

        def count_started(self, *, user_id: str, org_id: str | None, since: datetime) -> int:
            with self._gate:
                self.overlap += 1
                self.max_overlap = max(self.max_overlap, self.overlap)
            try:
                time.sleep(0.15)
                return super().count_started(user_id=user_id, org_id=org_id, since=since)
            finally:
                with self._gate:
                    self.overlap -= 1

    store = SlowPostgres(schema_url)
    Base.metadata.drop_all(store.engine)
    Base.metadata.create_all(store.engine)
    billing = PostgresBillingStore(engine=store.engine)
    settings = make_settings(tmp_path, quota_free=1, quota_mode="enforce")
    ok: list[str] = []
    blocked: list[int] = []
    errors: list[BaseException] = []

    def once(name: str) -> None:
        from fastapi import HTTPException

        try:
            job = accept_job(
                settings=settings,
                store=store,
                billing=billing,
                user_id="user_quota",
                org_id=None,
                filename=name,
                content_type="video/mp4",
                byte_size=4,
                object_key=new_object_key("user_quota", name),
                object_etag="abc",
            )
            ok.append(job.id)
        except HTTPException as exc:
            blocked.append(exc.status_code)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=once, args=(f"{name}.mp4",)) for name in ("one", "two")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert errors == []
    assert store.max_overlap == 1
    assert len(ok) == 1
    assert blocked == [402]
    assert store.count_started(
        user_id="user_quota",
        org_id=None,
        since=datetime(2020, 1, 1, tzinfo=timezone.utc),
    ) == 1


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
