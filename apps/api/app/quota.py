"""Plan limits for job creation.

Started jobs in the current period count, including ones that later fail.
Uploads stay on the short rate limit; the monthly cap is the job itself.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, Request

from secureai_shared.billing import effective_plan
from secureai_shared.settings import Settings


def enforce_job_quota(request: Request, user_id: str, org_id: str | None) -> None:
    settings: Settings = request.app.state.settings
    if settings.quota_mode == "unlimited":
        return

    billing = request.app.state.billing
    if org_id is not None:
        summary = billing.org_summary(org_id, user_id=user_id)
        if summary is None:
            raise HTTPException(status_code=403, detail="Not a member of this workspace")
        plan = effective_plan(summary.plan, summary.subscription_status)
        period_start = summary.current_period_start
        period_end = summary.current_period_end
    else:
        account = billing.user_account(user_id)
        plan = effective_plan(account.plan, account.subscription_status)
        period_start = account.current_period_start
        period_end = account.current_period_end

    start, _end = active_period(period_start, period_end, utc_now())
    used = request.app.state.store.count_started(user_id=user_id, org_id=org_id, since=start)
    limit = job_limit(settings, plan)
    if used < limit:
        return

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
