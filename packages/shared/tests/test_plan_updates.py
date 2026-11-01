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
                    "metadata": {"user_id": "user_owner", "org_id": "org_abc123", "plan": "pro"},
                    "line_items": {"data": [{"price": {"id": "price_team"}}]},
                }
            },
        },
        {"price_team": "team"},
    )
    assert update is not None
    assert update.org_id == "org_abc123"
    assert update.user_id is None
    assert update.plan == "team"


def test_unknown_price_does_not_fall_back_to_metadata_plan() -> None:
    update = plan_update_from_event(
        {
            "type": "customer.subscription.updated",
            "created": 50,
            "data": {
                "object": {
                    "id": "sub_x",
                    "customer": "cus_x",
                    "status": "active",
                    "metadata": {"user_id": "user_dev", "plan": "team"},
                    "items": {"data": [{"price": {"id": "price_other"}}]},
                }
            },
        },
        {"price_pro": "pro", "price_team": "team"},
    )
    assert update is not None
    assert update.plan is None
    assert update.status is None
    assert update.event_created == 50


def test_known_price_wins_over_metadata_plan() -> None:
    update = plan_update_from_event(
        {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_x",
                    "status": "active",
                    "metadata": {"user_id": "user_dev", "plan": "team"},
                    "items": {"data": [{"price": {"id": "price_pro"}}]},
                }
            },
        },
        {"price_pro": "pro"},
    )
    assert update is not None
    assert update.plan == "pro"
    assert update.status == "active"


def test_checkout_metadata_plan_is_not_a_fallback() -> None:
    unknown = plan_update_from_event(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_unknown",
                    "customer": "cus_x",
                    "subscription": "sub_x",
                    "payment_status": "paid",
                    "metadata": {"user_id": "user_dev", "plan": "team", "org_id": ""},
                    "line_items": {"data": [{"price": {"id": "price_other"}}]},
                }
            },
        },
        {"price_pro": "pro", "price_team": "team"},
    )
    assert unknown is not None
    assert unknown.plan is None
    assert unknown.status is None
    assert unknown.replaces_subscription is False

    recorded = plan_update_from_event(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_recorded",
                    "customer": "cus_x",
                    "subscription": "sub_x",
                    "payment_status": "paid",
                    "metadata": {"user_id": "user_dev", "plan": "team", "org_id": ""},
                }
            },
        },
        {"price_pro": "pro"},
        checkout_intents={"cs_recorded": "pro"},
    )
    assert recorded is not None
    assert recorded.plan == "pro"
    assert recorded.status == "active"

    missing = plan_update_from_event(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_x",
                    "subscription": "sub_x",
                    "payment_status": "paid",
                    "metadata": {"user_id": "user_dev", "plan": "pro", "org_id": ""},
                }
            },
        },
        {"price_pro": "pro"},
    )
    assert missing is not None
    assert missing.plan is None
    assert missing.status is None


def test_invoice_does_not_leave_a_terminal_status() -> None:
    from secureai_shared.billing import MemoryBillingStore

    prices = {"price_pro": "pro"}
    store = MemoryBillingStore()
    deleted = plan_update_from_event(
        {
            "type": "customer.subscription.deleted",
            "created": 200,
            "data": {
                "object": {
                    "id": "sub_x",
                    "customer": "cus_x",
                    "status": "canceled",
                    "metadata": {"user_id": "user_dev", "org_id": ""},
                }
            },
        },
        prices,
    )
    assert store.apply_stripe_event("evt_deleted", "customer.subscription.deleted", deleted) is True
    for event_id, kind, created, status in (
        ("evt_paid", "invoice.paid", 300, "active"),
        ("evt_failed", "invoice.payment_failed", 400, "past_due"),
    ):
        update = plan_update_from_event(
            {
                "type": kind,
                "created": created,
                "data": {
                    "object": {
                        "customer": "cus_x",
                        "subscription": "sub_x",
                        "metadata": {"user_id": "user_dev", "org_id": ""},
                    }
                },
            },
            prices,
        )
        assert update is not None
        assert update.invoice is True
        assert update.status == status
        assert store.apply_stripe_event(event_id, kind, update) is True
        account = store.user_account("user_dev")
        assert account.subscription_status == "canceled"
        assert account.plan == "free"


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


def _postgres_store():
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
    return store


def test_postgres_billing_round_trip() -> None:
    store = _postgres_store()

    update = plan_update_from_event(
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_pg",
                    "subscription": "sub_pg",
                    "payment_status": "paid",
                    "metadata": {"user_id": "user_pg", "plan": "team", "org_id": ""},
                    "line_items": {"data": [{"price": {"id": "price_pro"}}]},
                }
            },
        },
        {"price_pro": "pro"},
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


def test_postgres_terminal_invoice_hard_deletes_seats_and_checkout_intent() -> None:
    from sqlalchemy import text

    store = _postgres_store()
    prices = {"price_pro": "pro", "price_team": "team"}
    deleted = plan_update_from_event(
        {
            "type": "customer.subscription.deleted",
            "created": 200,
            "data": {
                "object": {
                    "id": "sub_pg",
                    "customer": "cus_pg",
                    "status": "canceled",
                    "metadata": {"user_id": "user_pg", "org_id": ""},
                }
            },
        },
        prices,
    )
    paid = plan_update_from_event(
        {
            "type": "invoice.paid",
            "created": 300,
            "data": {
                "object": {
                    "customer": "cus_pg",
                    "subscription": "sub_pg",
                    "metadata": {"user_id": "user_pg", "org_id": ""},
                }
            },
        },
        prices,
    )
    # The account row has to exist before a customer-only invoice can find it.
    assert store.apply_stripe_event("evt_del", "customer.subscription.deleted", deleted) is True
    assert store.apply_stripe_event("evt_inv", "invoice.paid", paid) is True
    account = store.user_account("user_pg")
    assert account.subscription_status == "canceled"
    assert account.plan == "free"

    org = store.create_org(name="Clamp", owner_user_id="user_owner")
    for user_id in ("user_a", "user_b", "user_c"):
        store.add_member(org.id, user_id, seat_limit=10)
    team = plan_update_from_event(
        {
            "type": "customer.subscription.updated",
            "created": 100,
            "data": {
                "object": {
                    "id": "sub_org",
                    "customer": "cus_org",
                    "status": "active",
                    "metadata": {"user_id": "user_owner", "org_id": org.id},
                    "items": {"data": [{"price": {"id": "price_team"}}]},
                }
            },
        },
        prices,
    )
    assert store.apply_stripe_event("evt_org_team", "customer.subscription.updated", team, free_seat_limit=2)
    assert len(store.members(org.id)) == 4
    team_end = plan_update_from_event(
        {
            "type": "customer.subscription.deleted",
            "created": 200,
            "data": {
                "object": {
                    "id": "sub_org",
                    "customer": "cus_org",
                    "status": "canceled",
                    "metadata": {"user_id": "user_owner", "org_id": org.id},
                }
            },
        },
        prices,
    )
    assert store.apply_stripe_event("evt_org_del", "customer.subscription.deleted", team_end, free_seat_limit=2)
    with store.engine.connect() as connection:
        rows = connection.execute(
            text("SELECT user_id, role FROM organization_members WHERE org_id = :org"),
            {"org": org.id},
        ).fetchall()
    assert {(row.user_id, row.role) for row in rows} == {("user_owner", "owner"), ("user_a", "member")}
    revived = plan_update_from_event(
        {
            "type": "customer.subscription.updated",
            "created": 400,
            "data": {
                "object": {
                    "id": "sub_org",
                    "customer": "cus_org",
                    "status": "active",
                    "metadata": {"user_id": "user_owner", "org_id": org.id},
                    "items": {"data": [{"price": {"id": "price_team"}}]},
                }
            },
        },
        prices,
    )
    assert store.apply_stripe_event("evt_org_back", "customer.subscription.updated", revived) is True
    with store.engine.connect() as connection:
        after = connection.execute(
            text("SELECT user_id FROM organization_members WHERE org_id = :org"),
            {"org": org.id},
        ).fetchall()
    assert {row.user_id for row in after} == {"user_owner", "user_a"}
    store.add_member(org.id, "user_c", seat_limit=10)
    assert store.membership(org.id, "user_c") == "member"

    store.remember_checkout(session_id="cs_pg", plan="pro", price_id="price_pro")
    assert store.checkout_plan("cs_pg", prices=prices) == "pro"
    assert store.checkout_plan("cs_pg", prices={"price_other": "team"}) is None
