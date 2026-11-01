"""Plan limits for job creation.

Started jobs in the current period count, including ones that later fail
during detection. A row that failed before it was published to Redis does
not count. A single create returns 503 in that case. A batch that already
queued some ids returns 202 and names the ids that did not queue.

The quota read and the job insert run while the billing account or
organization row is locked (`SELECT … FOR UPDATE` on Postgres, a per-subject
lock in memory). Two concurrent creates cannot both observe a free slot.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException

from secureai_shared.billing import BillingStore, OrgNotFound, effective_plan
from secureai_shared.models import JobRecord
from secureai_shared.settings import Settings
from secureai_shared.store import JobStore


def accept_job(
    *,
    settings: Settings,
    store: JobStore,
    billing: BillingStore,
    user_id: str,
    org_id: str | None,
    filename: str,
    content_type: str | None,
    byte_size: int | None,
    object_key: str,
    object_etag: str | None,
) -> JobRecord:
    """Insert a queued job if the caller is still under the plan cap."""

    if settings.quota_mode == "unlimited":
        return store.create(
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            byte_size=byte_size,
            object_key=object_key,
            object_etag=object_etag,
            org_id=org_id,
        )

    if org_id is not None:
        summary = billing.org_summary(org_id, user_id=user_id)
        if summary is None:
            raise HTTPException(status_code=403, detail="Not a member of this workspace")

    try:
        with billing.quota_lock(user_id=user_id, org_id=org_id):
            plan, period_start, period_end = _subject(billing, user_id, org_id)
            start, _end = active_period(period_start, period_end, utc_now())
            used = store.count_started(user_id=user_id, org_id=org_id, since=start)
            limit = job_limit(settings, plan)
            if used >= limit:
                _raise_quota(plan, used, limit)
            return store.create(
                user_id=user_id,
                filename=filename,
                content_type=content_type,
                byte_size=byte_size,
                object_key=object_key,
                object_etag=object_etag,
                org_id=org_id,
            )
    except OrgNotFound as exc:
        raise HTTPException(status_code=403, detail="Not a member of this workspace") from exc


def _subject(
    billing: BillingStore,
    user_id: str,
    org_id: str | None,
) -> tuple[str, datetime | None, datetime | None]:
    if org_id is not None:
        summary = billing.org_summary(org_id, user_id=user_id)
        if summary is None:
            raise HTTPException(status_code=403, detail="Not a member of this workspace")
        plan = effective_plan(summary.plan, summary.subscription_status)
        return plan, summary.current_period_start, summary.current_period_end
    account = billing.user_account(user_id)
    plan = effective_plan(account.plan, account.subscription_status)
    return plan, account.current_period_start, account.current_period_end


def _raise_quota(plan: str, used: int, limit: int) -> None:
    if plan == "free":
        raise HTTPException(
            status_code=402,
            detail=(
                f"Monthly job quota reached ({used} of {limit} on the free trial). "
                "Upgrade to continue."
            ),
        )
    label = "Team" if plan == "team" else "Pro"
    raise HTTPException(
        status_code=403,
        detail=f"Monthly job quota reached ({used} of {limit} on {label}).",
    )


def job_limit(settings: Settings, plan: str) -> int:
    if plan == "team":
        return settings.quota_team
    if plan == "pro":
        return settings.quota_pro
    return settings.quota_free


def seat_limit(settings: Settings, plan: str) -> int:
    if plan == "team":
        return settings.seat_limit_team
    return settings.seat_limit_free


def active_period(
    start: datetime | None,
    end: datetime | None,
    now: datetime,
) -> tuple[datetime, datetime]:
    if start is not None and end is not None and start <= now < end:
        return start, end
    return month_period(now)


def month_period(now: datetime) -> tuple[datetime, datetime]:
    start = now.astimezone(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
