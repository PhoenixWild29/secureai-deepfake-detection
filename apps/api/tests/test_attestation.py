"""Issue and verify signed report attestations."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.main import create_app
from secureai_shared.attestation import ALGORITHM, AttestationRecord
from conftest import make_settings
from secureai_shared.attestation import NOT_CONFIGURED
from secureai_shared.billing import MemoryBillingStore, PlanUpdate
from secureai_shared.limits import MemoryRateLimiter
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.report import LIMITATIONS, dump_report_detail
from secureai_shared.storage import FileSystemStorage, new_object_key
from secureai_shared.store import MemoryJobStore

AUTH = {"Authorization": "Bearer dev"}


def _pem() -> str:
    key = Ed25519PrivateKey.generate()
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _app(
    tmp_path: Path,
    *,
    pem: str | None = None,
    limiter=None,
    billing=None,
    attestations=None,
    **overrides: object,
):
    settings = make_settings(
        tmp_path,
        attestation_private_key="" if pem is None else pem,
        **overrides,
    )
    store = MemoryJobStore()
    storage = FileSystemStorage(tmp_path)
    app = create_app(
        settings=settings,
        store=store,
        queue=MemoryJobQueue(),
        storage=storage,
        limiter=limiter,
        billing=billing,
        attestations=attestations,
    )
    return app, store, storage


def _complete(client: TestClient, store: MemoryJobStore, storage: FileSystemStorage, headers: dict[str, str] | None = None) -> str:
    key = new_object_key("user_dev", "clip.mp4")
    storage.put(key, b"video-bytes", "video/mp4")
    created = client.post(
        "/v1/jobs",
        headers=headers or AUTH,
        json={"object_key": key, "filename": "clip.mp4", "content_type": "video/mp4"},
    )
    assert created.status_code == 202
    job_id = created.json()["id"]
    assert store.claim(job_id) is not None
    detail = dump_report_detail(
        "cpu-multisignal-v1",
        {"texture": 0.2, "motion": 0.1, "temporal": 0.3, "region": 0.0},
    )
    finished = store.complete(job_id, prediction="real", confidence=0.84, detail=detail)
    assert finished is not None
    return job_id


def test_sign_and_public_verify(tmp_path: Path) -> None:
    app, store, storage = _app(tmp_path, pem=_pem(), quota_mode="unlimited")
    with TestClient(app) as client:
        job_id = _complete(client, store, storage)
        waiting = client.get(f"/v1/jobs/{job_id}/report", headers=AUTH)
        assert waiting.status_code == 200

        issued = client.post(f"/v1/jobs/{job_id}/attest", headers=AUTH)
        assert issued.status_code == 200
        assert issued.headers["content-disposition"] == f'attachment; filename="{job_id}.attestation.json"'
        body = issued.json()
        assert body["algorithm"] == "Ed25519"
        assert body["key_id"] == "v1"
        assert "PRIVATE" not in issued.text
        payload = json.loads(body["payload"])
        assert payload["job_id"] == job_id
        assert payload["org_id"] is None
        assert payload["status"] == "completed"
        assert payload["prediction"] == "real"
        assert payload["confidence"] == 0.84
        assert payload["model"] == "cpu-multisignal-v1"
        assert payload["signals"]["texture"] == 0.2
        assert payload["limitations"] == LIMITATIONS

        again = client.post(f"/v1/jobs/{job_id}/attest", headers=AUTH)
        assert again.json()["signature"] == body["signature"]

        checked = client.post("/v1/attestations/verify", json=body)
        assert checked.status_code == 200
        assert checked.json()["valid"] is True
        public_pem = checked.json()["public_key"]
        assert public_pem.startswith("-----BEGIN PUBLIC KEY-----")
        load_pem_public_key(public_pem.encode()).verify(
            base64.b64decode(body["signature"]),
            body["payload"].encode(),
        )

        keys = client.get("/v1/attestations/keys")
        assert keys.status_code == 200
        assert keys.json()["keys"][0]["public_key"] == public_pem
        assert "PRIVATE" not in keys.text

        tampered = dict(body)
        tampered["payload"] = body["payload"].replace("real", "fake")
        rejected = client.post("/v1/attestations/verify", json=tampered)
        assert rejected.status_code == 200
        assert rejected.json() == {"valid": False}

        wrong_key = dict(body)
        wrong_key["key_id"] = "v2"
        mismatched = client.post("/v1/attestations/verify", json=wrong_key)
        assert mismatched.json() == {"valid": False}

        bad_sig = dict(body)
        signature = bad_sig["signature"]
        flipped = "A" if signature[10] != "A" else "B"
        bad_sig["signature"] = signature[:10] + flipped + signature[11:]
        assert client.post("/v1/attestations/verify", json=bad_sig).json() == {"valid": False}


def test_reissue_keeps_created_at(tmp_path: Path) -> None:
    app, store, storage = _app(tmp_path, pem=_pem(), quota_mode="unlimited")
    with TestClient(app) as client:
        job_id = _complete(client, store, storage)
        assert client.post(f"/v1/jobs/{job_id}/attest", headers=AUTH).status_code == 200
        first = app.state.attestations.get(job_id).created_at
        assert client.post(f"/v1/jobs/{job_id}/attest", headers=AUTH).status_code == 200
        assert app.state.attestations.get(job_id).created_at == first


def test_missing_key_is_503(tmp_path: Path) -> None:
    app, store, storage = _app(tmp_path, pem=None, quota_mode="unlimited")
    with TestClient(app) as client:
        job_id = _complete(client, store, storage)
        issued = client.post(f"/v1/jobs/{job_id}/attest", headers=AUTH)
        assert issued.status_code == 503
        assert issued.json()["detail"] == NOT_CONFIGURED
        checked = client.post(
            "/v1/attestations/verify",
            json={"payload": "{}", "signature": "YQ=="},
        )
        assert checked.status_code == 503
        assert checked.json()["detail"] == NOT_CONFIGURED
        keys = client.get("/v1/attestations/keys")
        assert keys.status_code == 503
        assert keys.json()["detail"] == NOT_CONFIGURED


def test_incomplete_and_foreign_jobs(tmp_path: Path) -> None:
    app, store, storage = _app(tmp_path, pem=_pem(), quota_mode="unlimited")
    with TestClient(app) as client:
        key = new_object_key("user_dev", "clip.mp4")
        storage.put(key, b"video-bytes", "video/mp4")
        created = client.post(
            "/v1/jobs",
            headers=AUTH,
            json={"object_key": key, "filename": "clip.mp4"},
        )
        job_id = created.json()["id"]
        queued = client.post(f"/v1/jobs/{job_id}/attest", headers=AUTH)
        assert queued.status_code == 409
        assert queued.json()["detail"] == "Job is not complete"
        assert client.post(f"/v1/jobs/{job_id}/attest").status_code == 401

        assert store.claim(job_id) is not None
        assert store.fail(job_id) is not None
        failed = client.post(f"/v1/jobs/{job_id}/attest", headers=AUTH)
        assert failed.status_code == 409

    outsider = TestClient(
        create_app(
            settings=make_settings(
                storage.root,
                dev_subject="user_other",
                attestation_private_key=_pem(),
                quota_mode="unlimited",
            ),
            store=store,
            queue=MemoryJobQueue(),
            storage=storage,
        )
    )
    with outsider:
        hidden = outsider.post(f"/v1/jobs/{job_id}/attest", headers=AUTH)
    assert hidden.status_code == 404


def test_free_plan_is_402_and_pro_can_issue(tmp_path: Path) -> None:
    pem = _pem()
    blocked_app, blocked_store, blocked_storage = _app(tmp_path / "free", pem=pem, quota_mode="enforce")
    with TestClient(blocked_app) as client:
        job_id = _complete(client, blocked_store, blocked_storage)
        blocked = client.post(f"/v1/jobs/{job_id}/attest", headers=AUTH)
    assert blocked.status_code == 402
    assert blocked.json()["detail"] == "Attestation requires a Pro or Team plan."

    billing = MemoryBillingStore()
    billing.apply_stripe_event(
        "evt_pro",
        "customer.subscription.updated",
        PlanUpdate(user_id="user_dev", plan="pro", status="active"),
    )
    allowed_app, allowed_store, allowed_storage = _app(
        tmp_path / "pro",
        pem=pem,
        quota_mode="enforce",
        billing=billing,
    )
    with TestClient(allowed_app) as client:
        job_id = _complete(client, allowed_store, allowed_storage)
        issued = client.post(f"/v1/jobs/{job_id}/attest", headers=AUTH)
    assert issued.status_code == 200


def test_workspace_plan_gates_the_org_job(tmp_path: Path) -> None:
    billing = MemoryBillingStore()
    app, store, storage = _app(tmp_path, pem=_pem(), quota_mode="enforce", billing=billing)
    with TestClient(app) as client:
        org = client.post("/v1/orgs", headers=AUTH, json={"name": "Studio"})
        assert org.status_code == 201
        org_id = org.json()["id"]
        headers = {**AUTH, "X-Org-Id": org_id}
        job_id = _complete(client, store, storage, headers)
        blocked = client.post(f"/v1/jobs/{job_id}/attest", headers=headers)
        assert blocked.status_code == 402
        billing.apply_stripe_event(
            "evt_team",
            "customer.subscription.updated",
            PlanUpdate(org_id=org_id, plan="team", status="past_due"),
        )
        issued = client.post(f"/v1/jobs/{job_id}/attest", headers=headers)
    assert issued.status_code == 200
    assert json.loads(issued.json()["payload"])["org_id"] == org_id


def test_verify_is_rate_limited(tmp_path: Path) -> None:
    limiter = MemoryRateLimiter({"attestations": 2}, 60)
    app, store, storage = _app(tmp_path, pem=_pem(), quota_mode="unlimited", limiter=limiter)
    with TestClient(app) as client:
        job_id = _complete(client, store, storage)
        issued = client.post(f"/v1/jobs/{job_id}/attest", headers=AUTH)
        assert issued.status_code == 200
        body = issued.json()
        assert client.post("/v1/attestations/verify", json=body).status_code == 200
        assert client.post("/v1/attestations/verify", json=body).status_code == 200
        limited = client.post("/v1/attestations/verify", json=body)
    assert limited.status_code == 429
    assert limited.json()["detail"] == "Too many requests"


class _ConflictStore:
    """First save raises the primary-key race after remembering the row."""

    def __init__(self, *, winner: AttestationRecord | None = None) -> None:
        self.row = winner
        self.calls = 0

    def get(self, job_id: str) -> AttestationRecord | None:
        if self.row is None or self.row.job_id != job_id:
            return None
        return self.row

    def save(self, record: AttestationRecord) -> AttestationRecord:
        self.calls += 1
        if self.row is None:
            self.row = record
        raise IntegrityError("INSERT", {}, Exception("duplicate key"))


def test_concurrent_first_attest_returns_the_stored_row(tmp_path: Path) -> None:
    store = _ConflictStore()
    app, jobs, storage = _app(tmp_path, pem=_pem(), quota_mode="unlimited", attestations=store)
    with TestClient(app) as client:
        job_id = _complete(client, jobs, storage)
        issued = client.post(f"/v1/jobs/{job_id}/attest", headers=AUTH)
    assert issued.status_code == 200
    body = issued.json()
    assert body["signature"]
    assert body["algorithm"] == ALGORITHM
    assert store.calls == 1
    assert store.row is not None
    assert body["payload"] == store.row.payload


def test_conflicting_attest_is_409_not_500(tmp_path: Path) -> None:
    from datetime import datetime, timezone

    winner = AttestationRecord(
        job_id="unused",
        key_id="other",
        algorithm=ALGORITHM,
        payload='{"job_id":"other"}',
        signature="bm90LXRoZS1zYW1l",
        created_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
    )
    store = _ConflictStore(winner=winner)
    app, jobs, storage = _app(tmp_path, pem=_pem(), quota_mode="unlimited", attestations=store)
    with TestClient(app) as client:
        job_id = _complete(client, jobs, storage)
        winner = AttestationRecord(
            job_id=job_id,
            key_id=winner.key_id,
            algorithm=winner.algorithm,
            payload=winner.payload,
            signature=winner.signature,
            created_at=winner.created_at,
        )
        store.row = winner
        conflict = client.post(f"/v1/jobs/{job_id}/attest", headers=AUTH)
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "Attestation already exists"
