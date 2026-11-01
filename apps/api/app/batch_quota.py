"""Quota check for a batch of new jobs.

``POST /v1/jobs`` calls ``accept_job``. A batch uses the same lock, plan
window, and error codes, and inserts every row or none. Stripe checkout
and webhooks are not involved.
"""

from __future__ import annotations

from fastapi import HTTPException

from app.quota import _raise_quota, _subject, active_period, job_limit, utc_now
from secureai_shared.billing import BillingStore, OrgNotFound
from secureai_shared.models import JobRecord
from secureai_shared.settings import Settings
from secureai_shared.store import JobStore


def accept_batch(
    *,
    settings: Settings,
    store: JobStore,
    billing: BillingStore,
    user_id: str,
    org_id: str | None,
    items: list[tuple[str, str | None, int, str, str | None]],
) -> list[JobRecord]:
    """Insert one queued job per item when the whole batch fits the cap.

    Each item is ``(filename, content_type, byte_size, object_key, object_etag)``.
    The check and the inserts share ``billing.quota_lock``, the same lock
    ``accept_job`` holds for a single create.
    """

    if not items:
        return []
    if settings.quota_mode == "unlimited":
        return _create_all(store, user_id, org_id, items)

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
            count = len(items)
            if used + count > limit:
                if used >= limit:
                    _raise_quota(plan, used, limit)
                raise _over_quota(plan, used, limit, count)
            return _create_all(store, user_id, org_id, items)
    except OrgNotFound as exc:
        raise HTTPException(status_code=403, detail="Not a member of this workspace") from exc


def _create_all(
    store: JobStore,
    user_id: str,
    org_id: str | None,
    items: list[tuple[str, str | None, int, str, str | None]],
) -> list[JobRecord]:
    jobs: list[JobRecord] = []
    for filename, content_type, byte_size, object_key, object_etag in items:
        jobs.append(
            store.create(
                user_id=user_id,
                filename=filename,
                content_type=content_type,
                byte_size=byte_size,
                object_key=object_key,
                object_etag=object_etag,
                org_id=org_id,
            )
        )
    return jobs


def _over_quota(plan: str, used: int, limit: int, count: int) -> HTTPException:
    if plan == "free":
        return HTTPException(
            status_code=402,
            detail=(
                f"Monthly job quota reached ({used} of {limit} on the free trial). "
                f"This batch asks for {count} jobs. Upgrade to continue."
            ),
        )
    label = "Team" if plan == "team" else "Pro"
    return HTTPException(
        status_code=403,
        detail=(
            f"Monthly job quota reached ({used} of {limit} on {label}). "
            f"This batch asks for {count} jobs."
        ),
    )
