"""Stripe Checkout, Customer Portal, webhooks, and workspace membership."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from app.auth import require_user
from app.quota import active_period, job_limit, seat_limit, utc_now
from app.stripe_client import StripeNotConfigured, StripeProviderError, StripeSignatureError
from app.tenancy import ORG_ID, active_org
from secureai_shared.billing import (
    ENTITLED_STATUSES,
    AlreadyMember,
    OrgNotFound,
    OrgSummary,
    OwnerRequired,
    SeatLimitReached,
    effective_plan,
    plan_update_from_event,
)
from secureai_shared.models import AuthContext
from secureai_shared.settings import Settings

logger = logging.getLogger("secureai.api.billing")

router = APIRouter()
_USER_ID = re.compile(r"\S{1,255}")
_ACTIVE_SUBSCRIPTION = (
    "This account already has a subscription. Open the billing portal to change it."
)


class OrgSummaryView(BaseModel):
    id: str
    name: str
    role: str
    plan: str


class MemberView(BaseModel):
    user_id: str
    role: str


class BillingView(BaseModel):
    scope: Literal["user", "org"]
    org_id: str | None
    org_name: str | None
    role: str | None
    plan: str
    subscription_status: str | None
    jobs_used: int
    jobs_limit: int | None
    period_start: datetime
    period_end: datetime
    quota_mode: Literal["enforce", "unlimited"]
    checkout_pro: bool
    checkout_team: bool
    portal_available: bool
    seats_used: int | None
    seats_limit: int | None
    members: list[MemberView]
    orgs: list[OrgSummaryView]


class CheckoutRequest(BaseModel):
    plan: Literal["pro", "team"]
    org_id: str | None = None


class PortalRequest(BaseModel):
    org_id: str | None = None


class CheckoutLink(BaseModel):
    url: str


class OrgCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class MemberCreate(BaseModel):
    user_id: str = Field(min_length=1, max_length=255)


class WebhookResult(BaseModel):
    received: bool
    duplicate: bool


@router.get("/v1/billing", response_model=BillingView)
def get_billing(
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> BillingView:
    org_id = active_org(request, user)
    return _view(request, user.subject, org_id)


@router.get("/v1/orgs", response_model=list[OrgSummaryView])
def list_orgs(
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> list[OrgSummaryView]:
    return _org_views(request.app.state.billing.list_orgs(user.subject))


@router.post("/v1/orgs", response_model=OrgSummaryView, status_code=201)
def create_org(
    body: OrgCreate,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> OrgSummaryView:
    name = _clean_name(body.name)
    created = request.app.state.billing.create_org(name=name, owner_user_id=user.subject)
    return OrgSummaryView(id=created.id, name=created.name, role=created.role, plan=created.plan)


@router.post("/v1/orgs/{org_id}/members", response_model=MemberView, status_code=201)
def add_member(
    org_id: str,
    body: MemberCreate,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> MemberView:
    _require_owner(request, org_id, user.subject)
    member_id = _clean_user_id(body.user_id)
    summary = request.app.state.billing.org_summary(org_id, user_id=user.subject)
    if summary is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    plan = effective_plan(summary.plan, summary.subscription_status)
    try:
        request.app.state.billing.add_member(
            org_id,
            member_id,
            seat_limit=seat_limit(request.app.state.settings, plan),
        )
    except OrgNotFound as exc:
        raise HTTPException(status_code=404, detail="Organization not found") from exc
    except AlreadyMember as exc:
        raise HTTPException(status_code=409, detail="That user is already a member.") from exc
    except SeatLimitReached as exc:
        raise HTTPException(status_code=403, detail="This workspace has no open seats.") from exc
    return MemberView(user_id=member_id, role="member")


@router.delete("/v1/orgs/{org_id}/members/{member_id}", status_code=204)
def remove_member(
    org_id: str,
    member_id: str,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> None:
    if ORG_ID.fullmatch(org_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    role = request.app.state.billing.membership(org_id, user.subject)
    if role is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    target = _clean_user_id(member_id)
    if role != "owner" and target != user.subject:
        raise HTTPException(status_code=403, detail="Only the owner can remove another member.")
    try:
        request.app.state.billing.remove_member(org_id, target)
    except OrgNotFound as exc:
        raise HTTPException(status_code=404, detail="Organization not found") from exc
    except OwnerRequired as exc:
        raise HTTPException(status_code=403, detail="The workspace owner cannot be removed.") from exc


@router.post("/v1/billing/checkout", response_model=CheckoutLink)
def create_checkout(
    body: CheckoutRequest,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> CheckoutLink:
    settings: Settings = request.app.state.settings
    org_id = _checkout_org(request, user, body)
    stripe = request.app.state.stripe
    if not stripe.checkout_ready(body.plan):
        raise HTTPException(status_code=503, detail="Billing is not configured")

    billing = request.app.state.billing
    if org_id is not None:
        summary = billing.org_summary(org_id, user_id=user.subject)
        if summary is None:
            raise HTTPException(status_code=404, detail="Organization not found")
        if summary.subscription_status in ENTITLED_STATUSES:
            raise HTTPException(status_code=409, detail=_ACTIVE_SUBSCRIPTION)
        existing = summary.stripe_customer_id
    else:
        account = billing.user_account(user.subject)
        # active, trialing, and past_due already have a Stripe subscription.
        # A second Checkout would create another one. Canceled and unpaid may
        # start a new subscription. past_due uses the portal to pay the invoice.
        if account.subscription_status in ENTITLED_STATUSES:
            raise HTTPException(status_code=409, detail=_ACTIVE_SUBSCRIPTION)
        existing = account.stripe_customer_id

    try:
        customer_id = stripe.ensure_customer(
            existing=existing,
            user_id=user.subject,
            org_id=org_id,
        )
        billing.attach_customer(
            user_id=None if org_id else user.subject,
            org_id=org_id,
            customer_id=customer_id,
            free_seat_limit=settings.seat_limit_free,
        )
        opened = stripe.checkout_url(
            customer_id=customer_id,
            price_id=stripe.price_for(body.plan),
            user_id=user.subject,
            org_id=org_id,
            plan=body.plan,
        )
        billing.remember_checkout(
            session_id=opened.session_id,
            plan=body.plan,
            price_id=stripe.price_for(body.plan),
        )
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail="Billing is not configured") from exc
    except StripeProviderError as exc:
        logger.exception("stripe checkout failed")
        raise HTTPException(status_code=502, detail="Billing provider unavailable") from exc
    logger.info("checkout started subject=%s plan=%s org=%s", user.subject, body.plan, org_id or "-")
    return CheckoutLink(url=opened.url)


@router.post("/v1/billing/portal", response_model=CheckoutLink)
def create_portal(
    body: PortalRequest,
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> CheckoutLink:
    org_id = _portal_org(request, user, body.org_id)
    stripe = request.app.state.stripe
    if not stripe.portal_ready():
        raise HTTPException(status_code=503, detail="Billing is not configured")
    billing = request.app.state.billing
    if org_id is not None:
        summary = billing.org_summary(org_id, user_id=user.subject)
        if summary is None or summary.role != "owner":
            raise HTTPException(status_code=403, detail="Only the workspace owner can manage billing.")
        customer_id = summary.stripe_customer_id
    else:
        customer_id = billing.user_account(user.subject).stripe_customer_id
    if not customer_id:
        raise HTTPException(status_code=409, detail="Start a subscription before managing billing.")
    try:
        url = stripe.portal_url(customer_id=customer_id)
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail="Billing is not configured") from exc
    except StripeProviderError as exc:
        logger.exception("stripe portal failed")
        raise HTTPException(status_code=502, detail="Billing provider unavailable") from exc
    return CheckoutLink(url=url)


@router.post("/v1/billing/webhook", response_model=WebhookResult)
async def stripe_webhook(request: Request) -> WebhookResult:
    """Stripe calls this. It is not a Clerk route. The signature is the auth."""

    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        event = request.app.state.stripe.parse_event(payload, signature)
    except StripeNotConfigured as exc:
        raise HTTPException(status_code=503, detail="Billing is not configured") from exc
    except StripeSignatureError as exc:
        raise HTTPException(status_code=400, detail="Invalid Stripe signature") from exc

    event_id = event.get("id")
    event_type = event.get("type")
    if not isinstance(event_id, str) or not event_id or not isinstance(event_type, str):
        raise HTTPException(status_code=400, detail="Invalid Stripe event")

    settings: Settings = request.app.state.settings
    prices = _price_map(settings)
    update = plan_update_from_event(
        event,
        prices,
        checkout_intents=_checkout_intents(request, event, prices),
    )
    fresh = request.app.state.billing.apply_stripe_event(
        event_id,
        event_type,
        update,
        free_seat_limit=settings.seat_limit_free,
    )
    logger.info("stripe webhook type=%s id=%s duplicate=%s", event_type, event_id, not fresh)
    return WebhookResult(received=True, duplicate=not fresh)


def _view(request: Request, user_id: str, org_id: str | None) -> BillingView:
    settings: Settings = request.app.state.settings
    billing = request.app.state.billing
    stripe = request.app.state.stripe
    clock = utc_now()
    orgs = _org_views(billing.list_orgs(user_id))
    unlimited = settings.quota_mode == "unlimited"

    if org_id is None:
        account = billing.user_account(user_id)
        plan = effective_plan(account.plan, account.subscription_status)
        start, end = active_period(account.current_period_start, account.current_period_end, clock)
        used = request.app.state.store.count_started(user_id=user_id, org_id=None, since=start)
        return BillingView(
            scope="user",
            org_id=None,
            org_name=None,
            role=None,
            plan=plan,
            subscription_status=account.subscription_status,
            jobs_used=used,
            jobs_limit=None if unlimited else job_limit(settings, plan),
            period_start=start,
            period_end=end,
            quota_mode=settings.quota_mode,  # type: ignore[arg-type]
            checkout_pro=stripe.checkout_ready("pro"),
            checkout_team=stripe.checkout_ready("team"),
            portal_available=bool(account.stripe_customer_id) and stripe.portal_ready(),
            seats_used=None,
            seats_limit=None,
            members=[],
            orgs=orgs,
        )

    summary = billing.org_summary(org_id, user_id=user_id)
    if summary is None:
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    plan = effective_plan(summary.plan, summary.subscription_status)
    start, end = active_period(summary.current_period_start, summary.current_period_end, clock)
    used = request.app.state.store.count_started(user_id=user_id, org_id=org_id, since=start)
    member_rows = [MemberView(user_id=item.user_id, role=item.role) for item in billing.members(org_id)]
    return BillingView(
        scope="org",
        org_id=summary.id,
        org_name=summary.name,
        role=summary.role,
        plan=plan,
        subscription_status=summary.subscription_status,
        jobs_used=used,
        jobs_limit=None if unlimited else job_limit(settings, plan),
        period_start=start,
        period_end=end,
        quota_mode=settings.quota_mode,  # type: ignore[arg-type]
        checkout_pro=stripe.checkout_ready("pro"),
        checkout_team=stripe.checkout_ready("team"),
        portal_available=bool(summary.stripe_customer_id) and stripe.portal_ready(),
        seats_used=summary.seat_count,
        seats_limit=seat_limit(settings, plan),
        members=member_rows,
        orgs=orgs,
    )


def _org_views(rows: list[OrgSummary]) -> list[OrgSummaryView]:
    return [
        OrgSummaryView(
            id=row.id,
            name=row.name,
            role=row.role,
            plan=effective_plan(row.plan, row.subscription_status),
        )
        for row in rows
    ]


def _checkout_org(request: Request, user: AuthContext, body: CheckoutRequest) -> str | None:
    if body.plan == "pro":
        if body.org_id:
            raise HTTPException(status_code=400, detail="Pro checkout is for the personal account.")
        return None
    org_id = body.org_id or request.headers.get("x-org-id")
    if not org_id:
        raise HTTPException(status_code=400, detail="Team checkout requires a workspace.")
    if ORG_ID.fullmatch(org_id) is None:
        raise HTTPException(status_code=400, detail="Invalid organization")
    _require_owner(request, org_id, user.subject)
    return org_id


def _portal_org(request: Request, user: AuthContext, body_org: str | None) -> str | None:
    header_org = active_org(request, user)
    if body_org and header_org and body_org != header_org:
        raise HTTPException(status_code=400, detail="Organization does not match the request.")
    org_id = body_org or header_org
    if org_id is None:
        return None
    if ORG_ID.fullmatch(org_id) is None:
        raise HTTPException(status_code=400, detail="Invalid organization")
    return org_id


def _require_owner(request: Request, org_id: str, user_id: str) -> None:
    if ORG_ID.fullmatch(org_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    role = request.app.state.billing.membership(org_id, user_id)
    if role is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if role != "owner":
        raise HTTPException(status_code=403, detail="Only the workspace owner can do that.")


def _checkout_intents(request: Request, event: dict[str, object], prices: dict[str, str]) -> dict[str, str]:
    """Plan recorded for this Checkout session, when the payload has no price id."""

    if event.get("type") != "checkout.session.completed":
        return {}
    data = event.get("data")
    obj = data.get("object") if isinstance(data, dict) else None
    session_id = obj.get("id") if isinstance(obj, dict) else None
    if not isinstance(session_id, str) or not session_id:
        return {}
    plan = request.app.state.billing.checkout_plan(session_id, prices=prices)
    if plan not in {"pro", "team"}:
        return {}
    return {session_id: plan}


def _price_map(settings: Settings) -> dict[str, str]:
    prices: dict[str, str] = {}
    if settings.stripe_price_pro:
        prices[settings.stripe_price_pro] = "pro"
    if settings.stripe_price_team:
        prices[settings.stripe_price_team] = "team"
    return prices


def _clean_name(name: str) -> str:
    cleaned = " ".join(name.split())
    if not cleaned or len(cleaned) > 80:
        raise HTTPException(status_code=400, detail="Invalid organization name")
    return cleaned


def _clean_user_id(user_id: str) -> str:
    cleaned = user_id.strip()
    if _USER_ID.fullmatch(cleaned) is None:
        raise HTTPException(status_code=400, detail="Invalid user id")
    return cleaned
