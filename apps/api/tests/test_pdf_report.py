"""PDF download for a completed detection report."""

from __future__ import annotations

import re
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from app.main import create_app
from app.pdf_report import render_job_report_pdf
from conftest import make_settings
from secureai_shared.billing import MemoryBillingStore, PlanUpdate
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.report import LIMITATIONS, dump_report_detail
from secureai_shared.storage import FileSystemStorage, new_object_key
from secureai_shared.store import MemoryJobStore

AUTH = {"Authorization": "Bearer dev"}
ISSUER = "https://example.clerk.accounts.dev"
_SIGNALS = {"texture": 0.2, "motion": 0.1, "temporal": 0.3, "region": 0.0}


def _app(tmp_path: Path, *, billing=None, **overrides: object):
    settings = make_settings(tmp_path, **overrides)
    store = MemoryJobStore()
    storage = FileSystemStorage(tmp_path)
    app = create_app(
        settings=settings,
        store=store,
        queue=MemoryJobQueue(),
        storage=storage,
        billing=billing,
    )
    return app, store, storage


def _complete(
    client: TestClient,
    store: MemoryJobStore,
    storage: FileSystemStorage,
    headers: dict[str, str] | None = None,
    *,
    filename: str = "clip.mp4",
    user_id: str = "user_dev",
) -> str:
    key = new_object_key(user_id, filename)
    storage.put(key, b"video-bytes", "video/mp4")
    created = client.post(
        "/v1/jobs",
        headers=headers or AUTH,
        json={"object_key": key, "filename": filename, "content_type": "video/mp4"},
    )
    assert created.status_code == 202
    job_id = created.json()["id"]
    assert store.claim(job_id) is not None
    detail = dump_report_detail("cpu-multisignal-v1", _SIGNALS)
    finished = store.complete(job_id, prediction="real", confidence=0.84, detail=detail)
    assert finished is not None
    return job_id


def _pdf_text(data: bytes) -> str:
    parts = [data.decode("latin-1", "replace")]
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        try:
            parts.append(zlib.decompress(match.group(1)).decode("latin-1"))
        except zlib.error:
            continue
    return "\n".join(parts)


def test_render_replaces_characters_outside_the_pdf_font() -> None:
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    data = render_job_report_pdf(
        job_id="job_abc123abc123",
        org_id=None,
        filename="视频.mp4",
        status="completed",
        prediction="real",
        confidence=0.84,
        model="cpu-multisignal-v1",
        signals=_SIGNALS,
        created_at=now,
        updated_at=now,
        limitations=LIMITATIONS,
    )
    assert data.startswith(b"%PDF")
    text = _pdf_text(data)
    assert "??.mp4" in text
    assert len(re.findall(rb"/Type /Page[^s]", data)) == 1


def test_completed_job_pdf_for_a_dev_workstation(tmp_path: Path) -> None:
    app, store, storage = _app(tmp_path, quota_mode="unlimited")
    with TestClient(app) as client:
        key = new_object_key("user_dev", "clip.mp4")
        storage.put(key, b"video-bytes", "video/mp4")
        created = client.post(
            "/v1/jobs",
            headers=AUTH,
            json={"object_key": key, "filename": "clip.mp4", "content_type": "video/mp4"},
        )
        job_id = created.json()["id"]
        queued = client.get(f"/v1/jobs/{job_id}/report.pdf", headers=AUTH)
        assert queued.status_code == 409
        assert queued.json()["detail"] == "Job is not complete"

        assert store.claim(job_id) is not None
        processing = client.get(f"/v1/jobs/{job_id}/report.pdf", headers=AUTH)
        assert processing.status_code == 409

        detail = dump_report_detail("cpu-multisignal-v1", _SIGNALS)
        assert store.complete(job_id, prediction="real", confidence=0.84, detail=detail) is not None
        exported = client.get(f"/v1/jobs/{job_id}/report.pdf", headers=AUTH)

        assert exported.status_code == 200
        assert exported.headers["content-type"] == "application/pdf"
        assert exported.headers["content-disposition"] == f'attachment; filename="{job_id}.pdf"'
        body = exported.content
        assert body.startswith(b"%PDF")
        assert body.rstrip().endswith(b"%%EOF")
        text = _pdf_text(body)
        assert "SecureAI Detection Report" in text
        assert job_id in text
        assert "Organization" in text
        assert "real" in text
        assert "0.84" in text
        assert "cpu-multisignal-v1" in text
        assert "Texture" in text
        assert "0.2" in text
        assert "not a trained deepfake classifier" in text
        assert len(re.findall(rb"/Type /Page[^s]", body)) == 1

        hidden = client.get(f"/v1/jobs/{job_id}/report.pdf")
        assert hidden.status_code == 401


def test_failed_and_foreign_jobs(tmp_path: Path) -> None:
    app, store, storage = _app(tmp_path, quota_mode="unlimited")
    with TestClient(app) as client:
        key = new_object_key("user_dev", "clip.mp4")
        storage.put(key, b"video-bytes", "video/mp4")
        created = client.post(
            "/v1/jobs",
            headers=AUTH,
            json={"object_key": key, "filename": "clip.mp4"},
        )
        job_id = created.json()["id"]
        assert store.claim(job_id) is not None
        assert store.fail(job_id) is not None
        failed = client.get(f"/v1/jobs/{job_id}/report.pdf", headers=AUTH)
        assert failed.status_code == 409
        missing = client.get("/v1/jobs/job_doesnotexist/report.pdf", headers=AUTH)
        assert missing.status_code == 404

    outsider = TestClient(
        create_app(
            settings=make_settings(storage.root, dev_subject="user_other", quota_mode="unlimited"),
            store=store,
            queue=MemoryJobQueue(),
            storage=storage,
        )
    )
    with outsider:
        forbidden = outsider.get(f"/v1/jobs/{job_id}/report.pdf", headers=AUTH)
    assert forbidden.status_code == 404


def test_free_plan_is_402_and_pro_can_download(tmp_path: Path) -> None:
    blocked_app, blocked_store, blocked_storage = _app(tmp_path / "free", quota_mode="enforce")
    with TestClient(blocked_app) as client:
        job_id = _complete(client, blocked_store, blocked_storage)
        report = client.get(f"/v1/jobs/{job_id}/report", headers=AUTH)
        assert report.status_code == 200
        assert report.json()["pdf_available"] is True
        blocked = client.get(f"/v1/jobs/{job_id}/report.pdf", headers=AUTH)
    assert blocked.status_code == 402
    assert blocked.json()["detail"] == "PDF export requires a Pro or Team plan."

    billing = MemoryBillingStore()
    billing.apply_stripe_event(
        "evt_pro",
        "customer.subscription.updated",
        PlanUpdate(user_id="user_dev", plan="pro", status="active"),
    )
    allowed_app, allowed_store, allowed_storage = _app(
        tmp_path / "pro",
        quota_mode="enforce",
        billing=billing,
    )
    with TestClient(allowed_app) as client:
        job_id = _complete(client, allowed_store, allowed_storage)
        exported = client.get(f"/v1/jobs/{job_id}/report.pdf", headers=AUTH)
    assert exported.status_code == 200
    assert exported.content.startswith(b"%PDF")


def test_workspace_plan_gates_the_org_job(tmp_path: Path) -> None:
    billing = MemoryBillingStore()
    app, store, storage = _app(tmp_path, quota_mode="enforce", billing=billing)
    with TestClient(app) as client:
        org = client.post("/v1/orgs", headers=AUTH, json={"name": "Studio"})
        assert org.status_code == 201
        org_id = org.json()["id"]
        headers = {**AUTH, "X-Org-Id": org_id}
        job_id = _complete(client, store, storage, headers)
        blocked = client.get(f"/v1/jobs/{job_id}/report.pdf", headers=headers)
        assert blocked.status_code == 402
        billing.apply_stripe_event(
            "evt_team",
            "customer.subscription.updated",
            PlanUpdate(org_id=org_id, plan="team", status="past_due"),
        )
        exported = client.get(f"/v1/jobs/{job_id}/report.pdf", headers=headers)
    assert exported.status_code == 200
    assert org_id in _pdf_text(exported.content)


def test_clerk_unlimited_still_requires_a_paid_plan(tmp_path: Path) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk["kid"] = "test-key"
    public_jwk["alg"] = "RS256"
    public_jwk["use"] = "sig"
    settings = make_settings(
        tmp_path,
        auth_mode="clerk",
        clerk_issuer=ISSUER,
        clerk_authorized_parties=(),
        quota_mode="unlimited",
    )
    store = MemoryJobStore()
    storage = FileSystemStorage(tmp_path)
    app = create_app(
        settings=settings,
        store=store,
        queue=MemoryJobQueue(),
        storage=storage,
        fetch_jwks=lambda: {"keys": [public_jwk]},
    )
    token = jwt.encode(
        {"sub": "user_clerk", "iss": ISSUER, "exp": int(time.time()) + 600},
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        job_id = _complete(client, store, storage, headers, user_id="user_clerk")
        blocked = client.get(f"/v1/jobs/{job_id}/report.pdf", headers=headers)
    assert blocked.status_code == 402
    assert blocked.json()["detail"] == "PDF export requires a Pro or Team plan."


def test_render_accepts_windows_1252_punctuation_and_caps_signals() -> None:
    now = datetime(2026, 11, 1, tzinfo=timezone.utc)
    signals = {
        "texture": 0.2,
        "motion": 0.1,
        "temporal": 0.3,
        "region": 0.0,
    }
    for index in range(20):
        signals[f"extra{index:02d}"] = 0.01
    data = render_job_report_pdf(
        job_id="job_subject\u2019id",
        org_id=None,
        filename="director\u2019s cut\u2014final.mp4",
        status="completed",
        prediction="real",
        confidence=0.84,
        model="cpu-multisignal-v1",
        signals=signals,
        created_at=now,
        updated_at=now,
        limitations=LIMITATIONS,
    )
    assert data.startswith(b"%PDF")
    text = _pdf_text(data)
    assert "director" in text
    assert "final.mp4" in text
    assert "Texture" in text
    assert "extra00" in text
    assert "extra07" in text
    assert "extra08" not in text
    assert "12 additional signals omitted." in text
    assert len(re.findall(rb"/Type /Page[^s]", data)) == 1
