"""Pro/Team API keys: mint, list, call, revoke."""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path

import pytest

import jwt
from httpx2 import Response
from alembic.config import Config
from alembic.script import ScriptDirectory
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from app.main import create_app
from app.stripe_client import StartedCheckout
from conftest import make_settings
from secureai_shared.api_keys import MemoryApiKeyStore, secret_hash
from secureai_shared.billing import MemoryBillingStore, PlanUpdate
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.report import dump_report_detail
from secureai_shared.storage import FileSystemStorage, new_object_key
from secureai_shared.store import MemoryJobStore

AUTH = {"Authorization": "Bearer dev"}
ISSUER = "https://example.clerk.accounts.dev"
_SIGNALS = {"texture": 0.2, "motion": 0.1, "temporal": 0.3, "region": 0.0}


def _app(tmp_path: Path, *, billing: MemoryBillingStore | None = None, **overrides: object):
    values = {"quota_mode": "enforce"}
    values.update(overrides)
    settings = make_settings(tmp_path, **values)
    store = MemoryJobStore()
    storage = FileSystemStorage(tmp_path)
    app = create_app(
        settings=settings,
        store=store,
        queue=MemoryJobQueue(),
        storage=storage,
        billing=billing if billing is not None else MemoryBillingStore(),
    )
    return app, store, storage


def _grant(billing: MemoryBillingStore, *, user_id: str | None = None, org_id: str | None = None, plan: str, status: str) -> None:
    billing.apply_stripe_event(
        f"evt_{plan}_{user_id or org_id}_{status}",
        "customer.subscription.updated",
        PlanUpdate(user_id=user_id, org_id=org_id, plan=plan, status=status),
    )


def _complete(client: TestClient, store: MemoryJobStore, storage: FileSystemStorage, headers: dict[str, str]) -> str:
    key = new_object_key("user_dev", "clip.mp4")
    storage.put(key, b"video-bytes", "video/mp4")
    created = client.post(
        "/v1/jobs",
        headers=headers,
        json={"object_key": key, "filename": "clip.mp4", "content_type": "video/mp4"},
    )
    assert created.status_code == 202, created.text
    job_id = created.json()["id"]
    assert store.claim(job_id) is not None
    detail = dump_report_detail("cpu-multisignal-v1", _SIGNALS)
    assert store.complete(job_id, prediction="real", confidence=0.84, detail=detail) is not None
    return job_id


def test_revision_is_head() -> None:
    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    assert ScriptDirectory.from_config(config).get_current_head() == "20261101_0008"


def test_free_plan_cannot_create_or_use_a_key(tmp_path: Path) -> None:
    app, _store, _storage = _app(tmp_path)
    with TestClient(app) as client:
        blocked = client.post("/v1/api-keys", headers=AUTH, json={"name": "laptop"})
        assert blocked.status_code == 402
        assert blocked.json()["detail"] == "API keys require a Pro or Team plan."
        listed = client.get("/v1/api-keys", headers=AUTH)
        assert listed.status_code == 200
        assert listed.json() == []

    unlimited, _store, _storage = _app(tmp_path / "dev", quota_mode="unlimited")
    with TestClient(unlimited) as client:
        still_blocked = client.post("/v1/api-keys", headers=AUTH, json={})
    assert still_blocked.status_code == 402


def test_pro_key_calls_report_then_revoke_is_401(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    billing = MemoryBillingStore()
    _grant(billing, user_id="user_dev", plan="pro", status="active")
    app, store, storage = _app(tmp_path, billing=billing)
    caplog.set_level(logging.INFO)
    with TestClient(app) as client:
        job_id = _complete(client, store, storage, AUTH)
        created = client.post("/v1/api-keys", headers=AUTH, json={"name": "laptop"})
        assert created.status_code == 201, created.text
        body = created.json()
        secret = body["secret"]
        assert secret.startswith("sai_")
        assert body["prefix"] == secret[:12]
        assert body["org_id"] is None
        assert "secret_hash" not in body
        assert secret_hash(secret) not in created.text
        assert secret not in caplog.text

        listed = client.get("/v1/api-keys", headers=AUTH)
        assert listed.status_code == 200
        rows = listed.json()
        assert len(rows) == 1
        assert rows[0]["id"] == body["id"]
        assert "secret" not in rows[0]
        assert "secret_hash" not in rows[0]
        assert secret not in listed.text
        assert secret_hash(secret) not in listed.text

        key_auth = {"Authorization": f"Bearer {secret}"}
        report = client.get(f"/v1/jobs/{job_id}/report", headers=key_auth)
        assert report.status_code == 200
        assert report.json()["job_id"] == job_id
        pdf = client.get(f"/v1/jobs/{job_id}/report.pdf", headers=key_auth)
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF")
        minted = client.post("/v1/api-keys", headers=key_auth, json={"name": "another"})
        assert minted.status_code == 403

        removed = client.delete(f"/v1/api-keys/{body['id']}", headers=AUTH)
        assert removed.status_code == 204
        again = client.delete(f"/v1/api-keys/{body['id']}", headers=AUTH)
        assert again.status_code == 204
        revoked = client.get(f"/v1/jobs/{job_id}/report", headers=key_auth)
        assert revoked.status_code == 401
        assert revoked.json()["detail"] == "Authentication required"
        after = client.get("/v1/api-keys", headers=AUTH)
        assert after.json()[0]["revoked_at"] is not None
        assert secret not in after.text

        _grant(billing, user_id="user_dev", plan="free", status="canceled")
        fresh = client.post("/v1/api-keys", headers=AUTH, json={"name": "after"})
        assert fresh.status_code == 402


def test_downgraded_key_cannot_call_a_report(tmp_path: Path) -> None:
    billing = MemoryBillingStore()
    _grant(billing, user_id="user_dev", plan="pro", status="active")
    app, store, storage = _app(tmp_path, billing=billing)
    with TestClient(app) as client:
        job_id = _complete(client, store, storage, AUTH)
        created = client.post("/v1/api-keys", headers=AUTH, json={"name": "laptop"})
        secret = created.json()["secret"]
        _grant(billing, user_id="user_dev", plan="free", status="canceled")
        blocked = client.get(
            f"/v1/jobs/{job_id}/report",
            headers={"Authorization": f"Bearer {secret}"},
        )
    assert blocked.status_code == 402
    assert blocked.json()["detail"] == "API keys require a Pro or Team plan."
    assert secret_hash(secret) not in blocked.text


def test_workspace_team_key_is_scoped_and_members_cannot_mint(tmp_path: Path) -> None:
    billing = MemoryBillingStore()
    _grant(billing, user_id="user_dev", plan="pro", status="active")
    app, store, storage = _app(tmp_path, billing=billing)
    member = create_app(
        settings=make_settings(tmp_path, quota_mode="enforce", dev_subject="user_member"),
        store=store,
        queue=MemoryJobQueue(),
        storage=storage,
        billing=billing,
    )
    with TestClient(app) as client, TestClient(member) as member_client:
        org = client.post("/v1/orgs", headers=AUTH, json={"name": "Studio"})
        assert org.status_code == 201
        org_id = org.json()["id"]
        headers = {**AUTH, "X-Org-Id": org_id}
        blocked = client.post("/v1/api-keys", headers=headers, json={"name": "ci"})
        assert blocked.status_code == 402
        _grant(billing, org_id=org_id, plan="team", status="past_due")
        added = client.post(
            f"/v1/orgs/{org_id}/members",
            headers=AUTH,
            json={"user_id": "user_member"},
        )
        assert added.status_code == 201
        denied = member_client.post(
            "/v1/api-keys",
            headers={**AUTH, "X-Org-Id": org_id},
            json={"name": "nope"},
        )
        assert denied.status_code == 403

        job_id = _complete(client, store, storage, headers)
        created = client.post("/v1/api-keys", headers=headers, json={"name": "ci"})
        assert created.status_code == 201
        secret = created.json()["secret"]
        assert created.json()["org_id"] == org_id
        personal = client.get("/v1/api-keys", headers=AUTH)
        assert all(row["id"] != created.json()["id"] for row in personal.json())

        key_auth = {"Authorization": f"Bearer {secret}"}
        report = client.get(f"/v1/jobs/{job_id}/report", headers=key_auth)
        assert report.status_code == 200
        other = client.post("/v1/orgs", headers=AUTH, json={"name": "Other"})
        mismatched = client.get(
            f"/v1/jobs/{job_id}/report",
            headers={**key_auth, "X-Org-Id": other.json()["id"]},
        )
        assert mismatched.status_code == 403
        missing = client.delete(f"/v1/api-keys/{created.json()['id']}", headers=AUTH)
        assert missing.status_code == 404
        removed = client.delete(f"/v1/api-keys/{created.json()['id']}", headers=headers)
        assert removed.status_code == 204
        dead = client.get(f"/v1/jobs/{job_id}", headers=key_auth)
        assert dead.status_code == 401


def test_creation_is_rate_limited(tmp_path: Path) -> None:
    billing = MemoryBillingStore()
    _grant(billing, user_id="user_dev", plan="pro", status="active")
    app, _store, _storage = _app(tmp_path, billing=billing, rate_limit_api_keys=2)
    with TestClient(app) as client:
        assert client.post("/v1/api-keys", headers=AUTH, json={"name": "one"}).status_code == 201
        assert client.post("/v1/api-keys", headers=AUTH, json={"name": "two"}).status_code == 201
        limited = client.post("/v1/api-keys", headers=AUTH, json={"name": "three"})
    assert limited.status_code == 429


def test_active_key_cap(tmp_path: Path) -> None:
    billing = MemoryBillingStore()
    _grant(billing, user_id="user_dev", plan="team", status="active")
    settings = make_settings(tmp_path, quota_mode="enforce")
    app = create_app(
        settings=settings,
        store=MemoryJobStore(),
        queue=MemoryJobQueue(),
        storage=FileSystemStorage(tmp_path),
        billing=billing,
        api_keys=MemoryApiKeyStore(max_active=1),
    )
    with TestClient(app) as client:
        assert client.post("/v1/api-keys", headers=AUTH, json={"name": "one"}).status_code == 201
        capped = client.post("/v1/api-keys", headers=AUTH, json={"name": "two"})
    assert capped.status_code == 409


def test_clerk_session_still_works_and_can_mint_a_key(tmp_path: Path) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    public_jwk["kid"] = "test-key"
    public_jwk["alg"] = "RS256"
    public_jwk["use"] = "sig"
    calls = {"n": 0}

    def fetch_jwks() -> dict[str, object]:
        calls["n"] += 1
        return {"keys": [public_jwk]}

    now = int(time.time())
    token = jwt.encode(
        {"sub": "user_clerk", "iss": ISSUER, "azp": "http://localhost:3000", "exp": now + 600},
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    billing = MemoryBillingStore()
    _grant(billing, user_id="user_clerk", plan="pro", status="active")
    app = create_app(
        settings=make_settings(
            tmp_path,
            auth_mode="clerk",
            clerk_issuer=ISSUER,
            clerk_authorized_parties=("http://localhost:3000",),
            quota_mode="enforce",
        ),
        store=MemoryJobStore(),
        queue=MemoryJobQueue(),
        storage=FileSystemStorage(tmp_path),
        billing=billing,
        fetch_jwks=fetch_jwks,
    )
    session = {"Authorization": f"Bearer {token}"}
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.json()["auth"] == "clerk"
        upload = client.post("/v1/uploads", headers=session, json={"filename": "clip.mp4"})
        assert upload.status_code == 200
        created = client.post("/v1/api-keys", headers=session, json={"name": "ci"})
        assert created.status_code == 201
        secret = created.json()["secret"]
        assert hashlib.sha256(secret.encode()).hexdigest() not in created.text
        before = calls["n"]
        junk = client.get("/v1/api-keys", headers={"Authorization": "Bearer sai_" + "a" * 40})
        assert junk.status_code == 401
        assert calls["n"] == before
        used = client.get("/v1/api-keys", headers={"Authorization": f"Bearer {secret}"})
        assert used.status_code == 403
        assert calls["n"] == before


def test_personal_key_uses_the_workspace_plan(tmp_path: Path) -> None:
    """A Pro personal key cannot call as a Free workspace.

    The effective plan is the workspace when ``X-Org-Id`` is set, and the
    personal plan otherwise. A dev session on that Free workspace is unchanged.
    """

    billing = MemoryBillingStore()
    _grant(billing, user_id="user_dev", plan="pro", status="active")
    app, store, storage = _app(tmp_path, billing=billing)
    outsider = create_app(
        settings=make_settings(tmp_path, quota_mode="enforce", dev_subject="user_other"),
        store=store,
        queue=MemoryJobQueue(),
        storage=storage,
        billing=billing,
    )
    with TestClient(app) as client, TestClient(outsider) as other:
        created = client.post("/v1/api-keys", headers=AUTH, json={"name": "laptop"})
        assert created.status_code == 201, created.text
        secret = created.json()["secret"]
        key_auth = {"Authorization": f"Bearer {secret}"}
        free = client.post("/v1/orgs", headers=AUTH, json={"name": "Free"})
        assert free.status_code == 201
        free_id = free.json()["id"]
        paid = client.post("/v1/orgs", headers=AUTH, json={"name": "Paid"})
        paid_id = paid.json()["id"]
        foreign = other.post("/v1/orgs", headers=AUTH, json={"name": "Foreign"})
        foreign_id = foreign.json()["id"]

        blocked = client.get("/v1/jobs", headers={**key_auth, "X-Org-Id": free_id})
        assert blocked.status_code == 402
        assert blocked.json()["detail"] == "API keys require a Pro or Team plan."
        pdf = client.get(
            "/v1/jobs/job_0123456789ab/report.pdf",
            headers={**key_auth, "X-Org-Id": free_id},
        )
        assert pdf.status_code == 402
        assert pdf.json()["detail"] == "API keys require a Pro or Team plan."
        posted = client.post(
            "/v1/jobs",
            headers={**key_auth, "X-Org-Id": free_id},
            json={"object_key": "uploads/user_dev/clip.mp4", "filename": "clip.mp4"},
        )
        assert posted.status_code == 402
        assert posted.json()["detail"] == "API keys require a Pro or Team plan."
        listed = client.get("/v1/api-keys", headers=AUTH)
        assert listed.json()[0]["last_used_at"] is None

        session_jobs = client.get("/v1/jobs", headers={**AUTH, "X-Org-Id": free_id})
        assert session_jobs.status_code == 200
        session_pdf = client.get(
            "/v1/jobs/job_0123456789ab/report.pdf",
            headers={**AUTH, "X-Org-Id": free_id},
        )
        assert session_pdf.status_code == 404
        stranger = client.get("/v1/jobs", headers={**key_auth, "X-Org-Id": foreign_id})
        assert stranger.status_code == 403
        invalid = client.get("/v1/jobs", headers={**key_auth, "X-Org-Id": "not-an-org"})
        assert invalid.status_code == 400

        _grant(billing, org_id=paid_id, plan="team", status="past_due")
        allowed = client.get("/v1/jobs", headers={**key_auth, "X-Org-Id": paid_id})
        assert allowed.status_code == 200
        _grant(billing, user_id="user_dev", plan="free", status="canceled")
        personal = client.get("/v1/jobs", headers=key_auth)
        assert personal.status_code == 402
        still_paid = client.get("/v1/jobs", headers={**key_auth, "X-Org-Id": paid_id})
        assert still_paid.status_code == 200
        minted = client.post(
            "/v1/api-keys",
            headers={**AUTH, "X-Org-Id": paid_id},
            json={"name": "ci"},
        )
        assert minted.status_code == 201, minted.text
        assert client.post("/v1/api-keys", headers=AUTH, json={"name": "nope"}).status_code == 402


def test_bound_key_follows_the_workspace_plan(tmp_path: Path) -> None:
    billing = MemoryBillingStore()
    app, _store, _storage = _app(tmp_path, billing=billing)
    with TestClient(app) as client:
        personal = client.post("/v1/api-keys", headers=AUTH, json={"name": "laptop"})
        assert personal.status_code == 402
        org = client.post("/v1/orgs", headers=AUTH, json={"name": "Studio"})
        org_id = org.json()["id"]
        _grant(billing, org_id=org_id, plan="team", status="active")
        created = client.post(
            "/v1/api-keys",
            headers={**AUTH, "X-Org-Id": org_id},
            json={"name": "ci"},
        )
        assert created.status_code == 201, created.text
        secret = created.json()["secret"]
        assert client.get("/v1/jobs", headers={"Authorization": f"Bearer {secret}"}).status_code == 200
        _grant(billing, org_id=org_id, plan="free", status="canceled")
        blocked = client.get("/v1/jobs", headers={"Authorization": f"Bearer {secret}"})
        assert blocked.status_code == 402
        assert blocked.json()["detail"] == "API keys require a Pro or Team plan."


def test_api_key_cannot_call_admin_health(tmp_path: Path) -> None:
    billing = MemoryBillingStore()
    _grant(billing, user_id="user_dev", plan="pro", status="active")
    app, _store, _storage = _app(tmp_path, billing=billing, admin_user_ids=("user_dev",))
    with TestClient(app) as client:
        created = client.post("/v1/api-keys", headers=AUTH, json={"name": "laptop"})
        assert created.status_code == 201, created.text
        secret = created.json()["secret"]
        denied = client.get("/v1/admin/health", headers={"Authorization": f"Bearer {secret}"})
        assert denied.status_code == 404
        assert denied.json()["detail"] == "Not Found"
        assert "postgres" not in denied.text
        assert "user_dev" not in denied.text
        allowed = client.get("/v1/admin/health", headers=AUTH)
        assert allowed.status_code in {200, 503}
        assert allowed.json()["status"] in {"ok", "degraded"}


def test_demoted_minter_workspace_key_is_revoked(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    billing = MemoryBillingStore()
    _grant(billing, user_id="user_dev", plan="pro", status="active")
    app, store, storage = _app(tmp_path, billing=billing)
    admin_app = create_app(
        settings=make_settings(tmp_path, quota_mode="enforce", dev_subject="user_admin"),
        store=store,
        queue=MemoryJobQueue(),
        storage=storage,
        billing=billing,
        api_keys=app.state.api_keys,
    )
    caplog.set_level(logging.INFO)
    with TestClient(app) as client, TestClient(admin_app) as admin_client:
        org = client.post("/v1/orgs", headers=AUTH, json={"name": "Studio"})
        assert org.status_code == 201
        org_id = org.json()["id"]
        _grant(billing, org_id=org_id, plan="team", status="active")
        added = client.post(
            f"/v1/orgs/{org_id}/members",
            headers=AUTH,
            json={"user_id": "user_admin"},
        )
        assert added.status_code == 201
        billing._members[org_id]["user_admin"] = "admin"
        headers = {**AUTH, "X-Org-Id": org_id}
        created = admin_client.post("/v1/api-keys", headers=headers, json={"name": "ci"})
        assert created.status_code == 201, created.text
        secret = created.json()["secret"]
        key_id = created.json()["id"]
        key_auth = {"Authorization": f"Bearer {secret}"}
        assert admin_client.get("/v1/jobs", headers=key_auth).status_code == 200
        owner = client.post("/v1/api-keys", headers=headers, json={"name": "owner"})
        assert owner.status_code == 201, owner.text
        owner_auth = {"Authorization": f"Bearer {owner.json()['secret']}"}

        billing._members[org_id]["user_admin"] = "member"
        blocked = admin_client.get("/v1/jobs", headers=key_auth)
        assert blocked.status_code == 401
        assert blocked.json()["detail"] == "Authentication required"
        assert secret not in blocked.text
        assert admin_client.get("/v1/jobs", headers=headers).status_code == 200
        assert client.get("/v1/jobs", headers=owner_auth).status_code == 200
        billing._members[org_id]["user_admin"] = "admin"
        assert admin_client.get("/v1/jobs", headers=key_auth).status_code == 401
        listed = client.get("/v1/api-keys", headers=headers)
        row = next(item for item in listed.json() if item["id"] == key_id)
        assert row["revoked_at"] is not None
        assert secret not in listed.text
        assert secret not in caplog.text
        assert "minter_not_manager" in caplog.text

        billing._members[org_id]["user_admin"] = "admin"
        second = admin_client.post("/v1/api-keys", headers=headers, json={"name": "next"})
        assert second.status_code == 201, second.text
        second_auth = {"Authorization": f"Bearer {second.json()['secret']}"}
        del billing._members[org_id]["user_admin"]
        assert admin_client.get("/v1/jobs", headers=second_auth).status_code == 401
        billing._members[org_id]["user_admin"] = "owner"
        assert admin_client.get("/v1/jobs", headers=second_auth).status_code == 401


def test_workspace_key_cannot_name_another_org(tmp_path: Path) -> None:
    """A workspace key is limited to its org on path and body ids too.

    ``X-Org-Id`` already rejected a different workspace. Member, webhook,
    Checkout, and portal routes take the organization from the path or the
    JSON body, and used to authorize that id from membership alone. A
    personal key still can, because it is not bound to one workspace.
    """

    billing = MemoryBillingStore()
    _grant(billing, user_id="user_dev", plan="pro", status="active")
    app, _store, _storage = _app(
        tmp_path,
        billing=billing,
        stripe_secret_key="sk_test_example",
        stripe_price_pro="price_pro",
        stripe_price_team="price_team",
    )
    other_url = "https://customer.example/hooks/secureai"
    other_secret = "whsec-other-workspace-secret"
    limit = "API key is limited to its workspace"
    with TestClient(app) as client:
        studio = client.post("/v1/orgs", headers=AUTH, json={"name": "Studio"})
        other = client.post("/v1/orgs", headers=AUTH, json={"name": "Elsewhere"})
        assert studio.status_code == 201
        assert other.status_code == 201
        studio_id = studio.json()["id"]
        other_id = other.json()["id"]
        _grant(billing, org_id=studio_id, plan="team", status="active")
        added = client.post(
            f"/v1/orgs/{other_id}/members",
            headers=AUTH,
            json={"user_id": "user_guest"},
        )
        assert added.status_code == 201
        saved = client.put(
            f"/v1/orgs/{other_id}/webhook",
            headers=AUTH,
            json={"url": other_url, "secret": other_secret},
        )
        assert saved.status_code == 200

        minted = client.post(
            "/v1/api-keys",
            headers={**AUTH, "X-Org-Id": studio_id},
            json={"name": "ci"},
        )
        assert minted.status_code == 201, minted.text
        secret = minted.json()["secret"]
        bearer = {"Authorization": f"Bearer {secret}"}
        scoped = {**bearer, "X-Org-Id": studio_id}
        personal = client.post("/v1/api-keys", headers=AUTH, json={"name": "laptop"})
        assert personal.status_code == 201, personal.text
        personal_auth = {"Authorization": f"Bearer {personal.json()['secret']}"}

        listed = client.get("/v1/orgs", headers=bearer)
        assert listed.status_code == 200
        assert {row["id"] for row in listed.json()} == {studio_id}
        assert "Elsewhere" not in listed.text
        billing_view = client.get("/v1/billing", headers=bearer)
        assert billing_view.status_code == 200
        assert billing_view.json()["org_id"] == studio_id
        assert {row["id"] for row in billing_view.json()["orgs"]} == {studio_id}
        assert "Elsewhere" not in billing_view.text
        created = client.post("/v1/orgs", headers=bearer, json={"name": "Nope"})
        assert created.status_code == 403
        assert created.json()["detail"] == limit
        assert len(client.get("/v1/orgs", headers=AUTH).json()) == 2

        def denied(response: Response) -> None:
            assert response.status_code == 403
            assert response.json()["detail"] == limit
            assert other_url not in response.text
            assert other_secret not in response.text

        denied(client.get(f"/v1/orgs/{other_id}/webhook", headers=bearer))
        denied(
            client.put(
                f"/v1/orgs/{other_id}/webhook",
                headers=scoped,
                json={"url": "https://evil.example/hook", "secret": other_secret},
            )
        )
        denied(client.delete(f"/v1/orgs/{other_id}/webhook", headers=bearer))
        denied(client.get(f"/v1/orgs/{other_id}/webhook/deliveries", headers=bearer))
        denied(client.get("/v1/orgs/not-an-org/webhook", headers=bearer))
        denied(
            client.post(
                f"/v1/orgs/{other_id}/members",
                headers=bearer,
                json={"user_id": "user_added"},
            )
        )
        denied(client.delete(f"/v1/orgs/{other_id}/members/user_guest", headers=bearer))
        endpoint = app.state.webhooks.get_endpoint(other_id)
        assert endpoint is not None
        assert endpoint.url == other_url
        assert endpoint.secret == other_secret
        assert billing.membership(other_id, "user_guest") == "member"
        assert billing.membership(other_id, "user_added") is None
        assert client.get("/v1/orgs/not-an-org/webhook", headers=AUTH).status_code == 404

        own = client.put(
            f"/v1/orgs/{studio_id}/webhook",
            headers=bearer,
            json={"url": "https://studio.example/hooks/secureai", "secret": "studio-signing-secret"},
        )
        assert own.status_code == 200
        assert own.json()["url"] == "https://studio.example/hooks/secureai"
        assert other_secret not in own.text
        member = client.post(
            f"/v1/orgs/{studio_id}/members",
            headers=bearer,
            json={"user_id": "user_guest"},
        )
        assert member.status_code == 201
        assert billing.membership(studio_id, "user_guest") == "member"

        calls: list[str | None] = []

        def checkout_url(**kwargs: object) -> StartedCheckout:
            org = kwargs.get("org_id")
            calls.append(org if isinstance(org, str) or org is None else str(org))
            return StartedCheckout(
                url="https://checkout.stripe.test/c/pay",
                session_id=f"cs_{len(calls)}",
            )

        stripe = app.state.stripe
        stripe.ensure_customer = lambda **_kwargs: "cus_test"  # type: ignore[method-assign]
        stripe.checkout_url = checkout_url  # type: ignore[method-assign]
        stripe.portal_url = lambda **_kwargs: "https://billing.stripe.test/p/session"  # type: ignore[method-assign]

        pro = client.post("/v1/billing/checkout", headers=bearer, json={"plan": "pro"})
        denied(pro)
        foreign = client.post(
            "/v1/billing/checkout",
            headers=bearer,
            json={"plan": "team", "org_id": other_id},
        )
        denied(foreign)
        portal = client.post("/v1/billing/portal", headers=bearer, json={"org_id": other_id})
        denied(portal)
        assert calls == []

        still = client.get(f"/v1/orgs/{other_id}/webhook", headers=personal_auth)
        assert still.status_code == 200
        assert still.json()["url"] == other_url
        personal_orgs = client.get("/v1/orgs", headers=personal_auth)
        assert {row["id"] for row in personal_orgs.json()} == {studio_id, other_id}
        personal_checkout = client.post(
            "/v1/billing/checkout",
            headers=personal_auth,
            json={"plan": "team", "org_id": other_id},
        )
        assert personal_checkout.status_code == 200
        assert calls == [other_id]

        # Studio stays entitled, so the bound key can still authenticate.
        # The personal account does not. Checkout with no org id has to hit
        # Studio (409) rather than open a personal Checkout (200).
        _grant(billing, user_id="user_dev", plan="free", status="canceled")
        billing.attach_customer(
            user_id=None,
            org_id=studio_id,
            customer_id="cus_studio",
            free_seat_limit=3,
        )
        team = client.post("/v1/billing/checkout", headers=bearer, json={"plan": "team"})
        assert team.status_code == 409, team.text
        assert "subscription" in team.json()["detail"]
        assert calls == [other_id]
        opened = client.post("/v1/billing/portal", headers=bearer, json={})
        assert opened.status_code == 200
        assert opened.json()["url"] == "https://billing.stripe.test/p/session"
        session_missing = client.post("/v1/billing/checkout", headers=AUTH, json={"plan": "team"})
        assert session_missing.status_code == 400


def test_dev_bearer_is_unchanged(tmp_path: Path) -> None:
    app, _store, _storage = _app(tmp_path)
    with TestClient(app) as client:
        assert client.get("/health").json()["auth"] == "dev"
        ok = client.post("/v1/uploads", headers=AUTH, json={"filename": "clip.mp4"})
        assert ok.status_code == 200
        junk = client.post("/v1/uploads", headers={"Authorization": "Bearer not-a-key"}, json={"filename": "clip.mp4"})
        assert junk.status_code == 401
        almost = client.post(
            "/v1/uploads",
            headers={"Authorization": "Bearer sai_short"},
            json={"filename": "clip.mp4"},
        )
        assert almost.status_code == 401
