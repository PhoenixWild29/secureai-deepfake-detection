"""Stripe event mapping and a Postgres billing round trip."""

import os

import pytest

from secureai_shared.billing import AlreadyMember, plan_update_from_event


def test_subscription_price_id_selects_the_plan() -> None:
    update = plan_update_from_event(
        {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_123",
                    "customer": "cus_123",
                    "status": "active",
                    "metadata": {"user_id": "user_dev", "org_id": ""},
                    "items": {"data": [{"price": {"id": "price_team"}}]},
                    "current_period_start": 1700000000,
                    "current_period_end": 1702592000,
                }
            },
        },
        {"price_team": "team", "price_pro": "pro"},
    )
    assert update is not None
    assert update.plan == "team"
    assert update.user_id == "user_dev"
    assert update.org_id is None
    assert update.status == "active"
    assert update.period_end is not None


def test_team_checkout_targets_the_org() -> None:
    update = plan_update_from_event(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_org",
                    "subscription": "sub_org",
                    "payment_status": "paid",
                    "metadata": {"user_id": "user_owner", "org_id": "org_abc123", "plan": "team"},
                }
            },
        },
        {},
    )
    assert update is not None
    assert update.org_id == "org_abc123"
    assert update.user_id is None
    assert update.plan == "team"


def test_unpaid_checkout_does_not_grant_pro() -> None:
    update = plan_update_from_event(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_123",
                    "payment_status": "unpaid",
                    "metadata": {"user_id": "user_dev", "plan": "pro", "org_id": ""},
                }
            },
        },
        {},
    )
    assert update is not None
    assert update.plan is None
    assert update.status == "incomplete"


def test_postgres_billing_round_trip() -> None:
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg://secureai:secureai@127.0.0.1:5432/secureai",
    )
    try:
        from secureai_shared.billing import PostgresBillingStore
        from secureai_shared.db import Base

        probe = PostgresBillingStore(url)
        with probe.engine.connect() as connection:
            connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS secureai_billing_test")
            connection.commit()
        probe.engine.dispose()
        schema_url = url + ("&" if "?" in url else "?") + "options=-csearch_path%3Dsecureai_billing_test"
        store = PostgresBillingStore(schema_url)
        Base.metadata.drop_all(store.engine)
        Base.metadata.create_all(store.engine)
    except Exception as exc:
        if os.environ.get("REQUIRE_SERVICES") == "1":
            pytest.fail(f"postgres unavailable: {exc}")
        pytest.skip(f"postgres unavailable: {exc}")

    update = plan_update_from_event(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_pg",
                    "subscription": "sub_pg",
                    "payment_status": "paid",
                    "metadata": {"user_id": "user_pg", "plan": "pro", "org_id": ""},
                }
            },
        },
        {},
    )
    assert store.apply_stripe_event("evt_pg", "checkout.session.completed", update) is True
    assert store.apply_stripe_event("evt_pg", "checkout.session.completed", update) is False
    account = store.user_account("user_pg")
    assert account.plan == "pro"
    assert account.stripe_customer_id == "cus_pg"
    assert account.subscription_status == "active"

    org = store.create_org(name="Studio", owner_user_id="user_pg")
    store.add_member(org.id, "user_member", seat_limit=3)
    assert store.membership(org.id, "user_member") == "member"
    with pytest.raises(AlreadyMember):
        store.add_member(org.id, "user_member", seat_limit=3)
