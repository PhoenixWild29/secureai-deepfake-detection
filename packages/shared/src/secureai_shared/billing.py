"""Workspaces and Stripe subscription state.

Clerk Organizations are not wired. A workspace is a Postgres row keyed by
Clerk user ids. Personal Pro lives on the user. Team lives on the org.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from secureai_shared.db import (
    BillingAccountRow,
    OrganizationMemberRow,
    OrganizationRow,
    StripeEventRow,
)

logger = logging.getLogger("secureai.billing")

ENTITLED_STATUSES = frozenset({"active", "trialing", "past_due"})
_TERMINAL_STATUSES = frozenset({"canceled", "unpaid", "incomplete_expired"})


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


def effective_plan(plan: str, status: str | None) -> str:
    """Paid plans count only while the subscription is entitled.

    A paid plan with no status is a manual grant (tests, local seeds).
    """

    if plan not in {"pro", "team"}:
        return "free"
    if status is None or status in ENTITLED_STATUSES:
        return plan
    return "free"


def plan_update_from_event(event: Mapping[str, object], prices: Mapping[str, str]) -> PlanUpdate | None:
    """Map a verified Stripe event into a billing write. Unknown types return None."""

    kind = event.get("type")
    data = event.get("data")
    if not isinstance(kind, str) or not isinstance(data, dict):
        return None
    obj = data.get("object")
    if not isinstance(obj, dict):
        return None
    if kind == "checkout.session.completed":
        return _from_checkout(obj)
    if kind == "customer.subscription.updated":
        return _from_subscription(obj, prices, deleted=False)
    if kind == "customer.subscription.deleted":
        return _from_subscription(obj, prices, deleted=True)
    if kind == "invoice.paid":
        return _from_invoice(obj, failed=False)
    if kind == "invoice.payment_failed":
        return _from_invoice(obj, failed=True)
    return None


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
    ) -> None: ...

    def apply_stripe_event(self, event_id: str, event_type: str, update: PlanUpdate | None) -> bool: ...


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
    price_id = _price_id(obj)
    if price_id and price_id in prices:
        mapped = prices[price_id]
        if mapped in {"pro", "team"}:
            return mapped
    user_id, _org_id = _scope(obj)
    del user_id
    meta = obj.get("metadata")
    if isinstance(meta, dict):
        named = meta.get("plan")
        if named in {"pro", "team"}:
            return named
    return None


def _target(user_id: str | None, org_id: str | None) -> tuple[str | None, str | None]:
    """Team checkout writes the org. Personal checkout writes the user."""

    if org_id:
        return None, org_id
    return user_id, None


def _from_checkout(obj: Mapping[str, object]) -> PlanUpdate | None:
    user_id, org_id = _scope(obj)
    user_id, org_id = _target(user_id, org_id)
    if user_id is None and org_id is None:
        return None
    paid = obj.get("payment_status") in {"paid", "no_payment_required"}
    plan = None
    status = "incomplete"
    if paid:
        meta = obj.get("metadata")
        named = meta.get("plan") if isinstance(meta, dict) else None
        if named in {"pro", "team"}:
            plan = named
        status = "active"
    return PlanUpdate(
        user_id=user_id,
        org_id=org_id,
        customer_id=_customer_id(obj),
        subscription_id=_subscription_id(obj),
        plan=plan,
        status=status,
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
    )


@dataclass
class _UserAccount:
    plan: str = "free"
    subscription_status: str | None = None
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
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
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None


class MemoryBillingStore:
    def __init__(self) -> None:
        self._users: dict[str, _UserAccount] = {}
        self._orgs: dict[str, _Org] = {}
        self._members: dict[str, dict[str, str]] = {}
        self._customers: dict[str, tuple[str, str]] = {}
        self._events: set[str] = set()
        self._lock = threading.Lock()

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

    def attach_customer(self, *, user_id: str | None, org_id: str | None, customer_id: str) -> None:
        with self._lock:
            self._apply_locked(
                PlanUpdate(user_id=user_id, org_id=org_id, customer_id=customer_id)
            )

    def apply_stripe_event(self, event_id: str, event_type: str, update: PlanUpdate | None) -> bool:
        del event_type
        with self._lock:
            if event_id in self._events:
                return False
            if update is not None:
                self._apply_locked(update)
            self._events.add(event_id)
            return True

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

    def _apply_locked(self, update: PlanUpdate) -> None:
        if update.org_id:
            org = self._orgs.get(update.org_id)
            if org is None:
                logger.warning("stripe event for unknown org_id=%s", update.org_id)
                return
            _merge_org(org, update)
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
                _merge_org(org, update)
                self._reindex("org", org.id, org.stripe_customer_id)
                return
            account = self._users.setdefault(ident, _UserAccount())
            _merge_user(account, update)
            self._reindex("user", ident, account.stripe_customer_id)

    def _reindex(self, kind: str, ident: str, customer_id: str | None) -> None:
        stale = [key for key, value in self._customers.items() if value == (kind, ident)]
        for key in stale:
            if key != customer_id:
                del self._customers[key]
        if customer_id:
            self._customers[customer_id] = (kind, ident)


def _merge_user(account: _UserAccount, update: PlanUpdate) -> None:
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


def _merge_org(org: _Org, update: PlanUpdate) -> None:
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
            engine = create_engine(database_url, pool_pre_ping=True)
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

    def attach_customer(self, *, user_id: str | None, org_id: str | None, customer_id: str) -> None:
        with self._session() as session:
            self._apply(session, PlanUpdate(user_id=user_id, org_id=org_id, customer_id=customer_id))
            session.commit()

    def apply_stripe_event(self, event_id: str, event_type: str, update: PlanUpdate | None) -> bool:
        with self._session() as session:
            if session.get(StripeEventRow, event_id) is not None:
                return False
            session.add(
                StripeEventRow(
                    id=event_id,
                    event_type=event_type[:128],
                    received_at=_now(),
                )
            )
            if update is not None:
                self._apply(session, update)
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                return False
            return True

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

    def _apply(self, session: Session, update: PlanUpdate) -> None:
        if update.org_id:
            org = session.get(OrganizationRow, update.org_id)
            if org is None:
                logger.warning("stripe event for unknown org_id=%s", update.org_id)
                return
            _merge_row(org, update)
            return
        if update.user_id:
            row = session.get(BillingAccountRow, update.user_id)
            if row is None:
                now = _now()
                row = BillingAccountRow(
                    user_id=update.user_id,
                    plan="free",
                    subscription_status=None,
                    stripe_customer_id=None,
                    stripe_subscription_id=None,
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
            select(BillingAccountRow).where(BillingAccountRow.stripe_customer_id == update.customer_id)
        )
        if account is not None:
            _merge_row(account, update)
            return
        org = session.scalar(
            select(OrganizationRow).where(OrganizationRow.stripe_customer_id == update.customer_id)
        )
        if org is None:
            logger.warning("stripe event for unknown customer")
            return
        _merge_row(org, update)

    def _session(self) -> Session:
        return self._session_factory()


def _merge_row(row: BillingAccountRow | OrganizationRow, update: PlanUpdate) -> None:
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
    row.updated_at = _now()


def _snapshot_row(row: BillingAccountRow) -> AccountSnapshot:
    return AccountSnapshot(
        plan=row.plan,
        subscription_status=row.subscription_status,
        stripe_customer_id=row.stripe_customer_id,
        stripe_subscription_id=row.stripe_subscription_id,
        current_period_start=row.current_period_start,
        current_period_end=row.current_period_end,
    )
