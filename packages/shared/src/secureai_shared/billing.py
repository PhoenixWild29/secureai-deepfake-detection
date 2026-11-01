"""Workspaces and Stripe subscription state.

Clerk Organizations are not wired. A workspace is a Postgres row keyed by
Clerk user ids. Personal Pro lives on the user. Team lives on the org.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from secureai_shared.db import (
    BillingAccountRow,
    CheckoutIntentRow,
    OrganizationMemberRow,
    OrganizationRow,
    StripeEventRow,
)

logger = logging.getLogger("secureai.billing")

# past_due keeps the paid plan for the dunning window. This service does not
# expire past_due on its own. Stripe billing settings (Smart Retries, then
# cancel or mark unpaid) must end that window with `unpaid` or `canceled`.
# Those terminal statuses drop the account to the free plan.
ENTITLED_STATUSES = frozenset({"active", "trialing", "past_due"})
_TERMINAL_STATUSES = frozenset({"canceled", "unpaid", "incomplete_expired"})
# Stripe retries a webhook for about three days. Keep the recorded Checkout
# plan a little longer, then drop it so abandoned sessions do not accumulate.
_CHECKOUT_INTENT_TTL = timedelta(days=7)


class OrgNotFound(Exception):
    """The workspace id is not in the store."""


class AlreadyMember(Exception):
    """That user is already a member of the workspace."""


class SeatLimitReached(Exception):
    """The workspace has no open seats."""


class OwnerRequired(Exception):
    """The owner membership cannot be removed."""


@dataclass(frozen=True)
class AccountSnapshot:
    plan: str = "free"
    subscription_status: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None


@dataclass(frozen=True)
class OrgSummary:
    id: str
    name: str
    role: str
    plan: str
    subscription_status: str | None
    stripe_customer_id: str | None
    seat_count: int
    current_period_start: datetime | None
    current_period_end: datetime | None


@dataclass(frozen=True)
class MemberRecord:
    user_id: str
    role: str


@dataclass(frozen=True)
class PlanUpdate:
    """Absolute fields from one Stripe event. None leaves the stored value."""

    user_id: str | None = None
    org_id: str | None = None
    customer_id: str | None = None
    subscription_id: str | None = None
    plan: str | None = None
    status: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    # Stripe Event.created (unix seconds). None when the payload has no timestamp.
    event_created: int | None = None
    # checkout.session.completed may replace the stored subscription id.
    # Update, delete, and invoice events for a different subscription must not.
    replaces_subscription: bool = False
    # invoice.paid and invoice.payment_failed must not leave a terminal status.
    invoice: bool = False


def effective_plan(plan: str, status: str | None) -> str:
    """Paid plans count only while the subscription is entitled.

    A paid plan with no status is a manual grant (tests, local seeds).
    `past_due` is entitled: the paid plan stays until Stripe ends dunning
    with `unpaid` or `canceled`.
    """

    if plan not in {"pro", "team"}:
        return "free"
    if status is None or status in ENTITLED_STATUSES:
        return plan
    return "free"


def _event_created(event: Mapping[str, object]) -> int | None:
    value = event.get("created")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value <= 0:
        return None
    return int(value)


def _touches_subscription(update: PlanUpdate) -> bool:
    return any(
        value is not None
        for value in (
            update.plan,
            update.status,
            update.subscription_id,
            update.period_start,
            update.period_end,
            update.event_created,
        )
    ) or update.replaces_subscription


def _resurrects(stored_status: str | None, incoming_status: str | None) -> bool:
    return stored_status in _TERMINAL_STATUSES and incoming_status in ENTITLED_STATUSES


def subscription_block_reason(
    *,
    stored_subscription_id: str | None,
    stored_status: str | None,
    stored_event_created: int | None,
    stored_period_end: datetime | None,
    update: PlanUpdate,
) -> str | None:
    """Return why this write must be ignored. None means apply it.

    A late `customer.subscription.updated` after `deleted` is older by
    Event.created (or by current_period_end when the event has no created).
    A delete or update for a previous subscription id cannot change the
    account after a replacement Checkout stored a new subscription id.
    Invoice events never move `canceled`, `unpaid`, or `incomplete_expired`,
    even when the invoice's Event.created is newer. That keeps Checkout
    from sticking on 409 after a late `invoice.paid` or `invoice.payment_failed`.
    """

    if not _touches_subscription(update):
        return None
    incoming_sub = update.subscription_id
    if stored_subscription_id and incoming_sub and incoming_sub != stored_subscription_id:
        if not update.replaces_subscription:
            return "subscription-mismatch"
        if (
            stored_event_created is not None
            and update.event_created is not None
            and update.event_created < stored_event_created
        ):
            return "stale-checkout"
        if stored_event_created is not None and update.event_created is None:
            return "checkout-without-timestamp"
        return None
    if _invoice_leaves_terminal(stored_status, update):
        return "terminal-invoice"
    if stored_event_created is not None and update.event_created is not None:
        if update.event_created < stored_event_created:
            return "stale-event"
        if update.event_created == stored_event_created and _resurrects(stored_status, update.status):
            return "stale-resubscribe"
    elif (
        stored_period_end is not None
        and update.period_end is not None
        and update.period_end < stored_period_end
    ):
        return "stale-period"
    elif _resurrects(stored_status, update.status) and update.event_created is None:
        if (
            update.period_end is None
            or stored_period_end is None
            or update.period_end <= stored_period_end
        ):
            return "stale-resubscribe"
    return None


def _invoice_leaves_terminal(stored_status: str | None, update: PlanUpdate) -> bool:
    """True when an invoice would overwrite a terminal subscription status."""

    if not update.invoice or stored_status not in _TERMINAL_STATUSES:
        return False
    return update.status is not None and update.status != stored_status


def plan_update_from_event(
    event: Mapping[str, object],
    prices: Mapping[str, str],
    *,
    checkout_intents: Mapping[str, str] | None = None,
) -> PlanUpdate | None:
    """Map a verified Stripe event into a billing write. Unknown types return None.

    `checkout_intents` maps a Checkout session id to the plan recorded when
    that session was created. It is used only when the event has no price id.
    """

    kind = event.get("type")
    data = event.get("data")
    if not isinstance(kind, str) or not isinstance(data, dict):
        return None
    obj = data.get("object")
    if not isinstance(obj, dict):
        return None
    if kind == "checkout.session.completed":
        update = _from_checkout(obj, prices, checkout_intents or {})
    elif kind == "customer.subscription.updated":
        update = _from_subscription(obj, prices, deleted=False)
    elif kind == "customer.subscription.deleted":
        update = _from_subscription(obj, prices, deleted=True)
    elif kind == "invoice.paid":
        update = _from_invoice(obj, failed=False)
    elif kind == "invoice.payment_failed":
        update = _from_invoice(obj, failed=True)
    else:
        return None
    if update is None:
        return None
    return replace(update, event_created=_event_created(event))


class BillingStore(Protocol):
    def user_account(self, user_id: str) -> AccountSnapshot: ...

    def org_summary(self, org_id: str, *, user_id: str) -> OrgSummary | None: ...

    def membership(self, org_id: str, user_id: str) -> str | None: ...

    def list_orgs(self, user_id: str) -> list[OrgSummary]: ...

    def members(self, org_id: str) -> list[MemberRecord]: ...

    def create_org(self, *, name: str, owner_user_id: str) -> OrgSummary: ...

    def add_member(self, org_id: str, user_id: str, *, seat_limit: int) -> None: ...

    def remove_member(self, org_id: str, user_id: str) -> None: ...

    def attach_customer(
        self,
        *,
        user_id: str | None,
        org_id: str | None,
        customer_id: str,
        free_seat_limit: int = 3,
    ) -> None: ...

    def remember_checkout(self, *, session_id: str, plan: str, price_id: str) -> None: ...

    def checkout_plan(self, session_id: str, *, prices: Mapping[str, str]) -> str | None: ...

    def apply_stripe_event(
        self,
        event_id: str,
        event_type: str,
        update: PlanUpdate | None,
        *,
        free_seat_limit: int = 3,
    ) -> bool: ...

    def quota_lock(self, *, user_id: str, org_id: str | None) -> Iterator[None]: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _prune_checkout_rows(session: Session, now: datetime) -> None:
    cutoff = now - _CHECKOUT_INTENT_TTL
    session.execute(delete(CheckoutIntentRow).where(CheckoutIntentRow.created_at < cutoff))


def _new_org_id() -> str:
    return f"org_{uuid4().hex[:12]}"


def _customer_id(obj: Mapping[str, object]) -> str | None:
    customer = obj.get("customer")
    if isinstance(customer, str) and customer:
        return customer
    if isinstance(customer, dict):
        cid = customer.get("id")
        if isinstance(cid, str) and cid:
            return cid
    return None


def _scope(obj: Mapping[str, object]) -> tuple[str | None, str | None]:
    meta = obj.get("metadata")
    if not isinstance(meta, dict):
        return None, None
    user = meta.get("user_id")
    org = meta.get("org_id")
    user_id = user if isinstance(user, str) and user else None
    org_id = org if isinstance(org, str) and org else None
    return user_id, org_id


def _unix(value: object) -> datetime | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if value <= 0:
        return None
    return datetime.fromtimestamp(value, timezone.utc)


def _period(obj: Mapping[str, object]) -> tuple[datetime | None, datetime | None]:
    start = _unix(obj.get("current_period_start"))
    end = _unix(obj.get("current_period_end"))
    if start is not None and end is not None:
        return start, end
    items = obj.get("items")
    data = items.get("data") if isinstance(items, dict) else None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        item = data[0]
        return _unix(item.get("current_period_start")), _unix(item.get("current_period_end"))
    return start, end


def _invoice_period(obj: Mapping[str, object]) -> tuple[datetime | None, datetime | None]:
    lines = obj.get("lines")
    data = lines.get("data") if isinstance(lines, dict) else None
    if isinstance(data, list) and data and isinstance(data[0], dict):
        period = data[0].get("period")
        if isinstance(period, dict):
            return _unix(period.get("start")), _unix(period.get("end"))
    return None, None


def _subscription_id(obj: Mapping[str, object]) -> str | None:
    sub = obj.get("subscription")
    if isinstance(sub, str) and sub:
        return sub
    if isinstance(sub, dict):
        sid = sub.get("id")
        if isinstance(sid, str) and sid:
            return sid
    parent = obj.get("parent")
    if isinstance(parent, dict):
        details = parent.get("subscription_details")
        if isinstance(details, dict):
            sid = details.get("subscription")
            if isinstance(sid, str) and sid:
                return sid
    return None


def _price_id(obj: Mapping[str, object]) -> str | None:
    items = obj.get("items")
    data = items.get("data") if isinstance(items, dict) else None
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        return None
    price = data[0].get("price")
    if isinstance(price, str) and price:
        return price
    if isinstance(price, dict):
        pid = price.get("id")
        if isinstance(pid, str) and pid:
            return pid
    return None


def _plan_from_subscription(obj: Mapping[str, object], prices: Mapping[str, str]) -> str | None:
    """Map only STRIPE_PRICE_PRO and STRIPE_PRICE_TEAM.

    metadata.plan is not a fallback. An unknown price must not upgrade the account.
    """

    price_id = _price_id(obj)
    if price_id and price_id in prices:
        mapped = prices[price_id]
        if mapped in {"pro", "team"}:
            return mapped
        logger.warning("configured stripe price id does not map to pro or team")
        return None
    if price_id:
        logger.warning("unknown stripe price id; not using metadata.plan")
    else:
        logger.warning("stripe subscription has no price id; not using metadata.plan")
    return None


def _target(user_id: str | None, org_id: str | None) -> tuple[str | None, str | None]:
    """Team checkout writes the org. Personal checkout writes the user."""

    if org_id:
        return None, org_id
    return user_id, None


def _price_from_value(price: object) -> str | None:
    if isinstance(price, str) and price:
        return price
    if isinstance(price, dict):
        pid = price.get("id")
        if isinstance(pid, str) and pid:
            return pid
    return None


def _checkout_price_id(obj: Mapping[str, object]) -> str | None:
    """Price id on the Checkout session, when Stripe included line items."""

    line_items = obj.get("line_items")
    data = line_items.get("data") if isinstance(line_items, dict) else None
    if isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            price_id = _price_from_value(item.get("price"))
            if price_id:
                return price_id
    display = obj.get("display_items")
    if isinstance(display, list):
        for item in display:
            if not isinstance(item, dict):
                continue
            price_id = _price_from_value(item.get("price"))
            if price_id:
                return price_id
    return None


def _known_plan(price_id: str | None, prices: Mapping[str, str]) -> str | None:
    if not price_id:
        return None
    mapped = prices.get(price_id)
    if mapped in {"pro", "team"}:
        return mapped
    return None


def _checkout_plan(
    obj: Mapping[str, object],
    prices: Mapping[str, str],
    checkout_intents: Mapping[str, str],
) -> str | None:
    """Plan from a known price id, or from the plan recorded at Checkout creation.

    metadata.plan is not a source. An unknown price id does not upgrade the account.
    """

    price_id = _checkout_price_id(obj)
    if price_id:
        plan = _known_plan(price_id, prices)
        if plan is None:
            logger.error("paid checkout was not applied: price id is not a configured pro or team price")
        return plan
    session_id = obj.get("id") if isinstance(obj.get("id"), str) else None
    remembered = checkout_intents.get(session_id) if session_id else None
    if remembered in {"pro", "team"}:
        return remembered
    logger.error("paid checkout was not applied: no known price id")
    return None


def _from_checkout(
    obj: Mapping[str, object],
    prices: Mapping[str, str],
    checkout_intents: Mapping[str, str],
) -> PlanUpdate | None:
    user_id, org_id = _scope(obj)
    user_id, org_id = _target(user_id, org_id)
    if user_id is None and org_id is None:
        return None
    paid = obj.get("payment_status") in {"paid", "no_payment_required"}
    plan = _checkout_plan(obj, prices, checkout_intents) if paid else None
    # A paid session we cannot name must not become an entitled status.
    # That would leave the account on the free plan and make Checkout return 409.
    status = "active" if plan is not None else ("incomplete" if not paid else None)
    return PlanUpdate(
        user_id=user_id,
        org_id=org_id,
        customer_id=_customer_id(obj),
        subscription_id=_subscription_id(obj),
        plan=plan,
        status=status,
        replaces_subscription=plan is not None or not paid,
    )


def _from_subscription(
    obj: Mapping[str, object],
    prices: Mapping[str, str],
    *,
    deleted: bool,
) -> PlanUpdate | None:
    user_id, org_id = _target(*_scope(obj))
    customer_id = _customer_id(obj)
    if user_id is None and org_id is None and customer_id is None:
        return None
    start, end = _period(obj)
    status = obj.get("status") if isinstance(obj.get("status"), str) else None
    if deleted:
        plan: str | None = "free"
        status = "canceled"
    elif status in _TERMINAL_STATUSES or status not in ENTITLED_STATUSES:
        plan = "free"
        status = status or "canceled"
    else:
        plan = _plan_from_subscription(obj, prices)
        if plan is None:
            # Do not record an entitlement we cannot name, and do not upgrade
            # from metadata.plan. Leave the stored plan and status alone.
            status = None
    sub_id = obj.get("id") if isinstance(obj.get("id"), str) else None
    return PlanUpdate(
        user_id=user_id,
        org_id=org_id,
        customer_id=customer_id,
        subscription_id=sub_id,
        plan=plan,
        status=status,
        period_start=start,
        period_end=end,
    )


def _invoice_scope(obj: Mapping[str, object]) -> tuple[str | None, str | None]:
    user_id, org_id = _scope(obj)
    if user_id or org_id:
        return _target(user_id, org_id)
    parent = obj.get("parent")
    if isinstance(parent, dict):
        details = parent.get("subscription_details")
        if isinstance(details, dict) and isinstance(details.get("metadata"), dict):
            return _target(*_scope({"metadata": details["metadata"]}))
    return None, None


def _from_invoice(obj: Mapping[str, object], *, failed: bool) -> PlanUpdate | None:
    user_id, org_id = _invoice_scope(obj)
    customer_id = _customer_id(obj)
    if user_id is None and org_id is None and customer_id is None:
        return None
    start, end = _invoice_period(obj)
    return PlanUpdate(
        user_id=user_id,
        org_id=org_id,
        customer_id=customer_id,
        subscription_id=_subscription_id(obj),
        plan=None,
        status="past_due" if failed else "active",
        period_start=start,
        period_end=end,
        invoice=True,
    )


@dataclass
class _UserAccount:
    plan: str = "free"
    subscription_status: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    stripe_event_created: int | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None


@dataclass
class _Org:
    id: str
    name: str
    created_at: datetime
    plan: str = "free"
    subscription_status: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    stripe_event_created: int | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None


class MemoryBillingStore:
    def __init__(self) -> None:
        self._users: dict[str, _UserAccount] = {}
        self._orgs: dict[str, _Org] = {}
        self._members: dict[str, dict[str, str]] = {}
        self._customers: dict[str, tuple[str, str]] = {}
        self._events: set[str] = set()
        self._checkout_intents: dict[str, tuple[str, str, datetime]] = {}
        self._lock = threading.Lock()
        self._quota_guards: dict[str, threading.Lock] = {}

    def user_account(self, user_id: str) -> AccountSnapshot:
        with self._lock:
            account = self._users.get(user_id)
            if account is None:
                return AccountSnapshot()
            return _snapshot_user(account)

    def org_summary(self, org_id: str, *, user_id: str) -> OrgSummary | None:
        with self._lock:
            return self._summary_locked(org_id, user_id)

    def membership(self, org_id: str, user_id: str) -> str | None:
        with self._lock:
            return self._members.get(org_id, {}).get(user_id)

    def list_orgs(self, user_id: str) -> list[OrgSummary]:
        with self._lock:
            found: list[OrgSummary] = []
            for org_id, members in self._members.items():
                if user_id not in members:
                    continue
                summary = self._summary_locked(org_id, user_id)
                if summary is not None:
                    found.append(summary)
            found.sort(key=lambda item: item.name.lower())
            return found

    def members(self, org_id: str) -> list[MemberRecord]:
        with self._lock:
            if org_id not in self._orgs:
                raise OrgNotFound(org_id)
            rows = [
                MemberRecord(user_id=user_id, role=role)
                for user_id, role in self._members.get(org_id, {}).items()
            ]
            rows.sort(key=lambda item: (item.role != "owner", item.user_id))
            return rows

    def create_org(self, *, name: str, owner_user_id: str) -> OrgSummary:
        now = _now()
        org = _Org(id=_new_org_id(), name=name, created_at=now)
        with self._lock:
            self._orgs[org.id] = org
            self._members[org.id] = {owner_user_id: "owner"}
            summary = self._summary_locked(org.id, owner_user_id)
        if summary is None:
            raise OrgNotFound(org.id)
        return summary

    def add_member(self, org_id: str, user_id: str, *, seat_limit: int) -> None:
        with self._lock:
            if org_id not in self._orgs:
                raise OrgNotFound(org_id)
            members = self._members.setdefault(org_id, {})
            if user_id in members:
                raise AlreadyMember(user_id)
            if len(members) >= seat_limit:
                raise SeatLimitReached(org_id)
            members[user_id] = "member"

    def remove_member(self, org_id: str, user_id: str) -> None:
        with self._lock:
            members = self._members.get(org_id)
            if org_id not in self._orgs or members is None or user_id not in members:
                raise OrgNotFound(org_id)
            if members[user_id] == "owner":
                raise OwnerRequired(user_id)
            del members[user_id]

    def attach_customer(
        self,
        *,
        user_id: str | None,
        org_id: str | None,
        customer_id: str,
        free_seat_limit: int = 3,
    ) -> None:
        with self._lock:
            self._apply_locked(
                PlanUpdate(user_id=user_id, org_id=org_id, customer_id=customer_id),
                free_seat_limit=free_seat_limit,
            )

    def remember_checkout(self, *, session_id: str, plan: str, price_id: str) -> None:
        if not session_id or plan not in {"pro", "team"} or not price_id:
            return
        now = _now()
        with self._lock:
            self._prune_checkouts_locked(now)
            self._checkout_intents[session_id] = (plan, price_id, now)

    def checkout_plan(self, session_id: str, *, prices: Mapping[str, str]) -> str | None:
        with self._lock:
            stored = self._checkout_intents.get(session_id)
        if stored is None:
            return None
        plan, price_id, _created_at = stored
        if _known_plan(price_id, prices) != plan:
            return None
        return plan

    def apply_stripe_event(
        self,
        event_id: str,
        event_type: str,
        update: PlanUpdate | None,
        *,
        free_seat_limit: int = 3,
    ) -> bool:
        del event_type
        with self._lock:
            self._prune_checkouts_locked(_now())
            if event_id in self._events:
                return False
            if update is not None:
                self._apply_locked(update, free_seat_limit=free_seat_limit)
            self._events.add(event_id)
            return True

    @contextmanager
    def quota_lock(self, *, user_id: str, org_id: str | None) -> Iterator[None]:
        """Serialize quota check and job insert for one account or workspace."""

        key = f"org:{org_id}" if org_id else f"user:{user_id}"
        with self._lock:
            guard = self._quota_guards.get(key)
            if guard is None:
                guard = threading.Lock()
                self._quota_guards[key] = guard
        with guard:
            yield

    def _summary_locked(self, org_id: str, user_id: str) -> OrgSummary | None:
        org = self._orgs.get(org_id)
        role = self._members.get(org_id, {}).get(user_id)
        if org is None or role is None:
            return None
        return OrgSummary(
            id=org.id,
            name=org.name,
            role=role,
            plan=org.plan,
            subscription_status=org.subscription_status,
            stripe_customer_id=org.stripe_customer_id,
            seat_count=len(self._members.get(org_id, {})),
            current_period_start=org.current_period_start,
            current_period_end=org.current_period_end,
        )

    def _apply_locked(self, update: PlanUpdate, *, free_seat_limit: int) -> None:
        if update.org_id:
            org = self._orgs.get(update.org_id)
            if org is None:
                logger.warning("stripe event for unknown org_id=%s", update.org_id)
                return
            if _merge_org(org, update) and _downgraded_to_free(update):
                self._clamp_org(org.id, free_seat_limit)
            self._reindex("org", org.id, org.stripe_customer_id)
            return
        if update.user_id:
            account = self._users.setdefault(update.user_id, _UserAccount())
            _merge_user(account, update)
            self._reindex("user", update.user_id, account.stripe_customer_id)
            return
        if update.customer_id:
            located = self._customers.get(update.customer_id)
            if located is None:
                logger.warning("stripe event for unknown customer")
                return
            kind, ident = located
            if kind == "org":
                org = self._orgs.get(ident)
                if org is None:
                    return
                if _merge_org(org, update) and _downgraded_to_free(update):
                    self._clamp_org(org.id, free_seat_limit)
                self._reindex("org", org.id, org.stripe_customer_id)
                return
            account = self._users.setdefault(ident, _UserAccount())
            _merge_user(account, update)
            self._reindex("user", ident, account.stripe_customer_id)

    def _clamp_org(self, org_id: str, free_seat_limit: int) -> None:
        org = self._orgs.get(org_id)
        if org is None or effective_plan(org.plan, org.subscription_status) != "free":
            return
        members = self._members.get(org_id)
        if members is None:
            return
        removed = _drop_newest_members(members, max(1, free_seat_limit))
        if removed:
            logger.info("clamped seats org_id=%s removed=%s", org_id, removed)

    def _prune_checkouts_locked(self, now: datetime) -> None:
        cutoff = now - _CHECKOUT_INTENT_TTL
        stale = [key for key, value in self._checkout_intents.items() if value[2] < cutoff]
        for key in stale:
            del self._checkout_intents[key]

    def _reindex(self, kind: str, ident: str, customer_id: str | None) -> None:
        stale = [key for key, value in self._customers.items() if value == (kind, ident)]
        for key in stale:
            if key != customer_id:
                del self._customers[key]
        if customer_id:
            self._customers[customer_id] = (kind, ident)


def _downgraded_to_free(update: PlanUpdate) -> bool:
    """True when this event ends the paid plan. Customer attaches do not."""

    if update.plan == "free":
        return True
    return update.status in _TERMINAL_STATUSES


def _drop_newest_members(members: dict[str, str], limit: int) -> int:
    """Remove the newest non-owners until the workspace fits `limit` seats."""

    removed = 0
    while len(members) > limit:
        removable = [user_id for user_id, role in members.items() if role != "owner"]
        if not removable:
            break
        del members[removable[-1]]
        removed += 1
    return removed


def _merge_user(account: _UserAccount, update: PlanUpdate) -> bool:
    reason = subscription_block_reason(
        stored_subscription_id=account.stripe_subscription_id,
        stored_status=account.subscription_status,
        stored_event_created=account.stripe_event_created,
        stored_period_end=account.current_period_end,
        update=update,
    )
    if reason is not None:
        logger.info("stripe subscription update ignored reason=%s", reason)
        return False
    if update.customer_id:
        account.stripe_customer_id = update.customer_id
    if update.subscription_id:
        account.stripe_subscription_id = update.subscription_id
    if update.plan is not None:
        account.plan = update.plan
    if update.status is not None:
        account.subscription_status = update.status
    if update.period_start is not None:
        account.current_period_start = update.period_start
    if update.period_end is not None:
        account.current_period_end = update.period_end
    if update.event_created is not None:
        account.stripe_event_created = update.event_created
    return True


def _merge_org(org: _Org, update: PlanUpdate) -> bool:
    reason = subscription_block_reason(
        stored_subscription_id=org.stripe_subscription_id,
        stored_status=org.subscription_status,
        stored_event_created=org.stripe_event_created,
        stored_period_end=org.current_period_end,
        update=update,
    )
    if reason is not None:
        logger.info("stripe subscription update ignored reason=%s", reason)
        return False
    if update.customer_id:
        org.stripe_customer_id = update.customer_id
    if update.subscription_id:
        org.stripe_subscription_id = update.subscription_id
    if update.plan is not None:
        org.plan = update.plan
    if update.status is not None:
        org.subscription_status = update.status
    if update.period_start is not None:
        org.current_period_start = update.period_start
    if update.period_end is not None:
        org.current_period_end = update.period_end
    if update.event_created is not None:
        org.stripe_event_created = update.event_created
    return True


def _snapshot_user(account: _UserAccount) -> AccountSnapshot:
    return AccountSnapshot(
        plan=account.plan,
        subscription_status=account.subscription_status,
        stripe_customer_id=account.stripe_customer_id,
        stripe_subscription_id=account.stripe_subscription_id,
        current_period_start=account.current_period_start,
        current_period_end=account.current_period_end,
    )


class PostgresBillingStore:
    def __init__(self, database_url: str | None = None, engine: object | None = None) -> None:
        if engine is None:
            if not database_url:
                raise RuntimeError("PostgresBillingStore requires a database url or an engine")
            engine = create_engine(database_url, pool_pre_ping=True, hide_parameters=True)
        self.engine = engine
        self._session_factory = sessionmaker(engine, expire_on_commit=False)  # type: ignore[arg-type]

    def user_account(self, user_id: str) -> AccountSnapshot:
        with self._session() as session:
            row = session.get(BillingAccountRow, user_id)
            if row is None:
                return AccountSnapshot()
            return _snapshot_row(row)

    def org_summary(self, org_id: str, *, user_id: str) -> OrgSummary | None:
        with self._session() as session:
            return self._summary(session, org_id, user_id)

    def membership(self, org_id: str, user_id: str) -> str | None:
        with self._session() as session:
            row = session.get(OrganizationMemberRow, {"org_id": org_id, "user_id": user_id})
            if row is None:
                return None
            return row.role

    def list_orgs(self, user_id: str) -> list[OrgSummary]:
        with self._session() as session:
            memberships = session.scalars(
                select(OrganizationMemberRow).where(OrganizationMemberRow.user_id == user_id)
            ).all()
            found = [self._summary(session, row.org_id, user_id) for row in memberships]
            orgs = [item for item in found if item is not None]
            orgs.sort(key=lambda item: item.name.lower())
            return orgs

    def members(self, org_id: str) -> list[MemberRecord]:
        with self._session() as session:
            if session.get(OrganizationRow, org_id) is None:
                raise OrgNotFound(org_id)
            rows = session.scalars(
                select(OrganizationMemberRow).where(OrganizationMemberRow.org_id == org_id)
            ).all()
            members = [MemberRecord(user_id=row.user_id, role=row.role) for row in rows]
            members.sort(key=lambda item: (item.role != "owner", item.user_id))
            return members

    def create_org(self, *, name: str, owner_user_id: str) -> OrgSummary:
        now = _now()
        org_id = _new_org_id()
        with self._session() as session:
            session.add(
                OrganizationRow(
                    id=org_id,
                    name=name,
                    plan="free",
                    subscription_status=None,
                    stripe_customer_id=None,
                    stripe_subscription_id=None,
                    current_period_start=None,
                    current_period_end=None,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.add(
                OrganizationMemberRow(
                    org_id=org_id,
                    user_id=owner_user_id,
                    role="owner",
                    created_at=now,
                )
            )
            session.commit()
            summary = self._summary(session, org_id, owner_user_id)
        if summary is None:
            raise OrgNotFound(org_id)
        return summary

    def add_member(self, org_id: str, user_id: str, *, seat_limit: int) -> None:
        with self._session() as session:
            org = session.scalar(
                select(OrganizationRow).where(OrganizationRow.id == org_id).with_for_update()
            )
            if org is None:
                raise OrgNotFound(org_id)
            existing = session.get(OrganizationMemberRow, {"org_id": org_id, "user_id": user_id})
            if existing is not None:
                raise AlreadyMember(user_id)
            seats = session.scalar(
                select(func.count())
                .select_from(OrganizationMemberRow)
                .where(OrganizationMemberRow.org_id == org_id)
            )
            if int(seats or 0) >= seat_limit:
                raise SeatLimitReached(org_id)
            session.add(
                OrganizationMemberRow(
                    org_id=org_id,
                    user_id=user_id,
                    role="member",
                    created_at=_now(),
                )
            )
            session.commit()

    def remove_member(self, org_id: str, user_id: str) -> None:
        with self._session() as session:
            org = session.scalar(
                select(OrganizationRow).where(OrganizationRow.id == org_id).with_for_update()
            )
            row = session.get(OrganizationMemberRow, {"org_id": org_id, "user_id": user_id})
            if org is None or row is None:
                raise OrgNotFound(org_id)
            if row.role == "owner":
                raise OwnerRequired(user_id)
            session.delete(row)
            session.commit()

    def attach_customer(
        self,
        *,
        user_id: str | None,
        org_id: str | None,
        customer_id: str,
        free_seat_limit: int = 3,
    ) -> None:
        with self._session() as session:
            self._apply(
                session,
                PlanUpdate(user_id=user_id, org_id=org_id, customer_id=customer_id),
                free_seat_limit=free_seat_limit,
            )
            session.commit()

    def remember_checkout(self, *, session_id: str, plan: str, price_id: str) -> None:
        if not session_id or plan not in {"pro", "team"} or not price_id:
            return
        now = _now()
        with self._session() as session:
            _prune_checkout_rows(session, now)
            row = session.get(CheckoutIntentRow, session_id)
            if row is None:
                session.add(
                    CheckoutIntentRow(
                        session_id=session_id,
                        plan=plan,
                        price_id=price_id,
                        created_at=now,
                    )
                )
            else:
                row.plan = plan
                row.price_id = price_id
                row.created_at = now
            session.commit()

    def checkout_plan(self, session_id: str, *, prices: Mapping[str, str]) -> str | None:
        with self._session() as session:
            row = session.get(CheckoutIntentRow, session_id)
            if row is None:
                return None
            plan, price_id = row.plan, row.price_id
        if _known_plan(price_id, prices) != plan:
            return None
        return plan

    def apply_stripe_event(
        self,
        event_id: str,
        event_type: str,
        update: PlanUpdate | None,
        *,
        free_seat_limit: int = 3,
    ) -> bool:
        now = _now()
        with self._session() as session:
            # Match MemoryBillingStore: prune before the duplicate check, and
            # keep that delete when this event id was already stored.
            _prune_checkout_rows(session, now)
            if session.get(StripeEventRow, event_id) is not None:
                session.commit()
                return False
            session.add(
                StripeEventRow(
                    id=event_id,
                    event_type=event_type[:128],
                    received_at=now,
                )
            )
            if update is not None:
                self._apply(session, update, free_seat_limit=free_seat_limit)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return False
            return True

    @contextmanager
    def quota_lock(self, *, user_id: str, org_id: str | None) -> Iterator[None]:
        """Hold the account or org row so two job inserts cannot both pass the cap.

        The row lock stays open across the caller's quota count and job insert.
        A second transaction blocks on `FOR UPDATE` until the first commits.
        """

        session = self._session()
        try:
            self._lock_quota_row(session, user_id, org_id)
            yield
        except Exception:
            session.rollback()
            raise
        else:
            session.commit()
        finally:
            session.close()

    def _lock_quota_row(self, session: Session, user_id: str, org_id: str | None) -> None:
        if org_id:
            org = session.scalar(
                select(OrganizationRow).where(OrganizationRow.id == org_id).with_for_update()
            )
            if org is None:
                raise OrgNotFound(org_id)
            return
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        now = _now()
        session.execute(
            pg_insert(BillingAccountRow)
            .values(
                user_id=user_id,
                plan="free",
                subscription_status=None,
                stripe_customer_id=None,
                stripe_subscription_id=None,
                stripe_event_created=None,
                current_period_start=None,
                current_period_end=None,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        session.flush()
        locked = session.scalar(
            select(BillingAccountRow)
            .where(BillingAccountRow.user_id == user_id)
            .with_for_update()
        )
        if locked is None:
            raise RuntimeError("billing account lock failed")

    def _summary(self, session: Session, org_id: str, user_id: str) -> OrgSummary | None:
        org = session.get(OrganizationRow, org_id)
        member = session.get(OrganizationMemberRow, {"org_id": org_id, "user_id": user_id})
        if org is None or member is None:
            return None
        seats = session.scalar(
            select(func.count())
            .select_from(OrganizationMemberRow)
            .where(OrganizationMemberRow.org_id == org_id)
        )
        return OrgSummary(
            id=org.id,
            name=org.name,
            role=member.role,
            plan=org.plan,
            subscription_status=org.subscription_status,
            stripe_customer_id=org.stripe_customer_id,
            seat_count=int(seats or 0),
            current_period_start=org.current_period_start,
            current_period_end=org.current_period_end,
        )

    def _apply(self, session: Session, update: PlanUpdate, *, free_seat_limit: int) -> None:
        if update.org_id:
            org = session.scalar(
                select(OrganizationRow).where(OrganizationRow.id == update.org_id).with_for_update()
            )
            if org is None:
                logger.warning("stripe event for unknown org_id=%s", update.org_id)
                return
            if _merge_row(org, update) and _downgraded_to_free(update):
                self._clamp_org(session, org, free_seat_limit)
            return
        if update.user_id:
            row = session.scalar(
                select(BillingAccountRow)
                .where(BillingAccountRow.user_id == update.user_id)
                .with_for_update()
            )
            if row is None:
                now = _now()
                row = BillingAccountRow(
                    user_id=update.user_id,
                    plan="free",
                    subscription_status=None,
                    stripe_customer_id=None,
                    stripe_subscription_id=None,
                    stripe_event_created=None,
                    current_period_start=None,
                    current_period_end=None,
                    created_at=now,
                    updated_at=now,
                )
                session.add(row)
            _merge_row(row, update)
            return
        if not update.customer_id:
            return
        account = session.scalar(
            select(BillingAccountRow)
            .where(BillingAccountRow.stripe_customer_id == update.customer_id)
            .with_for_update()
        )
        if account is not None:
            _merge_row(account, update)
            return
        org = session.scalar(
            select(OrganizationRow)
            .where(OrganizationRow.stripe_customer_id == update.customer_id)
            .with_for_update()
        )
        if org is None:
            logger.warning("stripe event for unknown customer")
            return
        if _merge_row(org, update) and _downgraded_to_free(update):
            self._clamp_org(session, org, free_seat_limit)

    def _clamp_org(self, session: Session, org: OrganizationRow, free_seat_limit: int) -> None:
        if effective_plan(org.plan, org.subscription_status) != "free":
            return
        limit = max(1, free_seat_limit)
        rows = session.scalars(
            select(OrganizationMemberRow)
            .where(OrganizationMemberRow.org_id == org.id)
            .order_by(
                OrganizationMemberRow.created_at.desc(),
                OrganizationMemberRow.user_id.desc(),
            )
        ).all()
        overflow = len(rows) - limit
        if overflow <= 0:
            return
        removed = 0
        for row in rows:
            if removed >= overflow:
                break
            if row.role == "owner":
                continue
            session.delete(row)
            removed += 1
        if removed:
            logger.info("clamped seats org_id=%s removed=%s", org.id, removed)

    def _session(self) -> Session:
        return self._session_factory()


def _merge_row(row: BillingAccountRow | OrganizationRow, update: PlanUpdate) -> bool:
    reason = subscription_block_reason(
        stored_subscription_id=row.stripe_subscription_id,
        stored_status=row.subscription_status,
        stored_event_created=row.stripe_event_created,
        stored_period_end=row.current_period_end,
        update=update,
    )
    if reason is not None:
        logger.info("stripe subscription update ignored reason=%s", reason)
        return False
    if update.customer_id:
        row.stripe_customer_id = update.customer_id
    if update.subscription_id:
        row.stripe_subscription_id = update.subscription_id
    if update.plan is not None:
        row.plan = update.plan
    if update.status is not None:
        row.subscription_status = update.status
    if update.period_start is not None:
        row.current_period_start = update.period_start
    if update.period_end is not None:
        row.current_period_end = update.period_end
    if update.event_created is not None:
        row.stripe_event_created = update.event_created
    row.updated_at = _now()
    return True


def _snapshot_row(row: BillingAccountRow) -> AccountSnapshot:
    return AccountSnapshot(
        plan=row.plan,
        subscription_status=row.subscription_status,
        stripe_customer_id=row.stripe_customer_id,
        stripe_subscription_id=row.stripe_subscription_id,
        current_period_start=row.current_period_start,
        current_period_end=row.current_period_end,
    )
