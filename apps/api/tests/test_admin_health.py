"""Admin health is authenticated. Public /health stays shallow."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from conftest import _client, make_settings
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.storage import FileSystemStorage
from secureai_shared.store import MemoryJobStore
from secureai_shared.reporting import error_reporting_enabled


def test_public_health_does_not_probe_dependencies(stack) -> None:
    client, _, _, _ = stack
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "secureai-api", "auth": "dev"}
    assert error_reporting_enabled() is False


def test_admin_health_rejects_anonymous_and_junk_tokens(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, admin_user_ids=("user_dev",))
    client, _, _, _ = _client(tmp_path, settings)
    with client:
        missing = client.get("/v1/admin/health")
        junk = client.get("/v1/admin/health", headers={"Authorization": "Bearer not-a-jwt"})
    assert missing.status_code == 401
    assert junk.status_code == 401
    assert missing.json()["detail"] == "Authentication required"
    assert "postgres" not in missing.text
    assert "user_dev" not in missing.text


def test_admin_health_forbids_non_admin(tmp_path: Path) -> None:
    settings = make_settings(tmp_path, admin_user_ids=("user_admin",))
    client, _, _, _ = _client(tmp_path, settings)
    with client:
        response = client.get("/v1/admin/health", headers={"Authorization": "Bearer dev"})
    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"
    assert "user_admin" not in response.text
    assert "postgres" not in response.text
    assert settings.database_url not in response.text


def test_admin_health_ok_with_mocked_dependencies(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("secureai_shared.health.check_postgres", lambda store: None)
    monkeypatch.setattr("secureai_shared.health.check_redis", lambda queue: None)
    monkeypatch.setattr("secureai_shared.health.check_storage", lambda storage: None)
    settings = make_settings(tmp_path, admin_user_ids=("user_dev",))
    client, _, _, _ = _client(tmp_path, settings)
    with client:
        response = client.get("/v1/admin/health", headers={"Authorization": "Bearer dev"})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["storage_backend"] == "filesystem"
    assert body["postgres"]["status"] == "ok"
    assert body["redis"]["status"] == "ok"
    assert body["storage"]["status"] == "ok"
    assert settings.database_url not in response.text
    assert str(tmp_path) not in response.text


def test_admin_health_degraded_hides_the_exception(tmp_path: Path, monkeypatch) -> None:
    def explode(store: object) -> None:
        del store
        raise RuntimeError("postgresql://app:dbpassword@db.internal/secureai")

    monkeypatch.setattr("secureai_shared.health.check_postgres", explode)
    monkeypatch.setattr("secureai_shared.health.check_redis", lambda queue: None)
    monkeypatch.setattr("secureai_shared.health.check_storage", lambda storage: None)
    settings = make_settings(tmp_path, admin_user_ids=("user_dev",))
    client, _, _, _ = _client(tmp_path, settings)
    with client:
        response = client.get("/v1/admin/health", headers={"Authorization": "Bearer dev"})
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "degraded"
    assert body["postgres"]["status"] == "error"
    assert body["redis"]["status"] == "ok"
    assert "dbpassword" not in response.text
    assert "db.internal" not in response.text
    assert "detail" not in body


def test_unhandled_exception_is_captured_without_echoing_it(tmp_path: Path, monkeypatch) -> None:
    seen: list[BaseException] = []
    monkeypatch.setattr("app.main.capture_exception", seen.append)
    app = create_app(
        settings=make_settings(tmp_path),
        store=MemoryJobStore(),
        queue=MemoryJobQueue(),
        storage=FileSystemStorage(tmp_path),
    )

    @app.get("/_test/boom")
    def boom() -> None:
        raise RuntimeError("Bearer super-secret-token")

    # ServerErrorMiddleware returns the handler body, then re-raises so a
    # server can log it. The test client would surface that raise.
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test/boom")
    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert "super-secret-token" not in response.text
    assert len(seen) == 1
    assert isinstance(seen[0], RuntimeError)


def test_create_app_leaves_reporting_disabled_without_dsn(tmp_path: Path) -> None:
    client, _, _, _ = _client(tmp_path, make_settings(tmp_path))
    assert client.app.version == "0.8.0"
    assert error_reporting_enabled() is False
