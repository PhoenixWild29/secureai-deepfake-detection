"""Signed report attestation.

Issuing uses the same job visibility as ``GET /v1/jobs/{id}/report``.
Verify and the public key do not use Clerk. The private key stays in
``ATTESTATION_PRIVATE_KEY`` and is never returned.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from app.auth import require_user
from app.routes import get_job
from app.tenancy import active_org
from secureai_shared.attestation import (
    ALGORITHM,
    NOT_CONFIGURED,
    AttestationKey,
    AttestationRecord,
    attestation_payload,
    may_issue_attestation,
)
from secureai_shared.billing import effective_plan
from secureai_shared.models import AuthContext, JobRecord, JobStatus
from secureai_shared.report import LIMITATIONS, load_report_detail

logger = logging.getLogger("secureai.api.attestation")

router = APIRouter()

PLAN_REQUIRED = "Attestation requires a Pro or Team plan."
_PAYLOAD_LIMIT = 65_536


class AttestationIssue(BaseModel):
    """Signed report. ``payload`` is the exact string that was signed."""

    payload: str
    signature: str
    key_id: str
    algorithm: str


class VerifyRequest(BaseModel):
    payload: str = Field(min_length=1, max_length=_PAYLOAD_LIMIT)
    signature: str = Field(min_length=1, max_length=512)
    key_id: str | None = Field(default=None, max_length=64)


class VerifyResult(BaseModel):
    valid: bool
    key_id: str | None = None
    algorithm: str | None = None
    public_key: str | None = None


class AttestationPublicKey(BaseModel):
    key_id: str
    algorithm: str
    public_key: str


class AttestationKeys(BaseModel):
    keys: list[AttestationPublicKey]


def _client_host(request: Request) -> str:
    """TCP peer. ``X-Forwarded-For`` is not read.

    Behind a reverse proxy this is the proxy address, so every caller shares
    one window. Trusting the header would let a client choose a fresh key.
    """

    client = request.client
    if client is None or not client.host:
        return "unknown"
    return client.host


def _limit_public(request: Request) -> None:
    if not request.app.state.limiter.allow("attestations", _client_host(request)):
        raise HTTPException(status_code=429, detail="Too many requests")


def _configured_key(request: Request) -> AttestationKey:
    key = request.app.state.attestation_key
    if not isinstance(key, AttestationKey):
        raise HTTPException(status_code=503, detail=NOT_CONFIGURED)
    return key


def _require_plan(request: Request, user: AuthContext, org_id: str | None) -> None:
    settings = request.app.state.settings
    billing = request.app.state.billing
    if org_id is not None:
        summary = billing.org_summary(org_id, user_id=user.subject)
        if summary is None:
            raise HTTPException(status_code=403, detail="Not a member of this workspace")
        plan = effective_plan(summary.plan, summary.subscription_status)
    else:
        account = billing.user_account(user.subject)
        plan = effective_plan(account.plan, account.subscription_status)
    if may_issue_attestation(auth_mode=settings.auth_mode, quota_mode=settings.quota_mode, plan=plan):
        return
    raise HTTPException(status_code=402, detail=PLAN_REQUIRED)


def _payload(job: JobRecord) -> str:
    model, signals = load_report_detail(job.detail)
    return attestation_payload(
        job_id=job.id,
        org_id=job.org_id,
        prediction=job.prediction,
        confidence=job.confidence,
        model=model,
        signals=signals,
        updated_at=job.updated_at,
        limitations=LIMITATIONS,
    )


@router.post("/v1/jobs/{job_id}/attest", response_model=AttestationIssue)
def issue_attestation(
    job_id: str,
    request: Request,
    response: Response,
    user: Annotated[AuthContext, Depends(require_user)],
) -> AttestationIssue:
    """Sign a completed job this caller can read.

    The same payload and key return the stored signature. A free plan is 402
    unless this process is ``AUTH_MODE=dev`` with ``QUOTA_MODE=unlimited``.
    """

    job = get_job(job_id, request, user)
    if job.status is not JobStatus.completed:
        raise HTTPException(status_code=409, detail="Job is not complete")
    key = _configured_key(request)
    org_id = active_org(request, user)
    _require_plan(request, user, org_id)
    payload = _payload(job)
    signature = key.sign(payload)
    record = AttestationRecord(
        job_id=job.id,
        key_id=key.key_id,
        algorithm=ALGORITHM,
        payload=payload,
        signature=signature,
        created_at=datetime.now(timezone.utc),
    )
    try:
        stored = request.app.state.attestations.save(record)
    except IntegrityError:
        # The store normally absorbs a concurrent first insert. If it still
        # raises, return the winner (200) or 409. Never an unhandled 500.
        logger.info("attestation insert conflict job_id=%s", job.id)
        found = request.app.state.attestations.get(job.id)
        if (
            found is None
            or found.payload != record.payload
            or found.key_id != record.key_id
            or found.signature != record.signature
        ):
            raise HTTPException(status_code=409, detail="Attestation already exists") from None
        stored = found
    logger.info("attestation job_id=%s key_id=%s", job.id, stored.key_id)
    response.headers["Content-Disposition"] = f'attachment; filename="{job.id}.attestation.json"'
    return AttestationIssue(
        payload=stored.payload,
        signature=stored.signature,
        key_id=stored.key_id,
        algorithm=stored.algorithm,
    )


@router.post(
    "/v1/attestations/verify",
    response_model=VerifyResult,
    response_model_exclude_none=True,
)
def verify_attestation(body: VerifyRequest, request: Request) -> VerifyResult:
    """Check a signature with the current key. No session is required.

    ``payload`` is verified as given. A valid result includes the public key
    that accepted it. Invalid signatures are ``valid: false``, not an error.
    Only ``ATTESTATION_KEY_ID`` is loaded. After that id or the private key
    changes, a signature made with the previous key does not verify.

    The rate limit key is the TCP peer, not ``X-Forwarded-For``. Behind a
    reverse proxy every caller shares one window.
    """

    _limit_public(request)
    key = _configured_key(request)
    if not key.verify(body.payload, body.signature, body.key_id):
        return VerifyResult(valid=False)
    return VerifyResult(
        valid=True,
        key_id=key.key_id,
        algorithm=key.algorithm,
        public_key=key.public_pem,
    )


@router.get("/v1/attestations/keys", response_model=AttestationKeys)
def attestation_keys(request: Request) -> AttestationKeys:
    """Public key for the current ``ATTESTATION_KEY_ID``. No session is required.

    Older key ids are not returned. The same TCP-peer rate limit as verify
    applies, and ``X-Forwarded-For`` is not trusted.
    """

    _limit_public(request)
    key = _configured_key(request)
    return AttestationKeys(
        keys=[
            AttestationPublicKey(
                key_id=key.key_id,
                algorithm=key.algorithm,
                public_key=key.public_pem,
            )
        ]
    )
