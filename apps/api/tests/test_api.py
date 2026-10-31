import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from secureai_shared.queue import MemoryJobQueue


@pytest.fixture
def client() -> TestClient:
    application = create_app(MemoryJobQueue())
    with TestClient(application) as test_client:
        yield test_client


def test_module_app_health() -> None:
    from app.main import app

    with TestClient(app) as test_client:
        response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "secureai-api"}


def test_create_and_fetch_job(client: TestClient) -> None:
    created = client.post(
        "/v1/jobs",
        json={"filename": "clip.mp4", "content_type": "video/mp4", "byte_size": 42},
    )
    assert created.status_code == 202
    body = created.json()
    assert body["status"] == "queued"
    assert body["filename"] == "clip.mp4"
    fetched = client.get(f"/v1/jobs/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]


def test_missing_job(client: TestClient) -> None:
    missing = client.get("/v1/jobs/job_0123456789ab")
    assert missing.status_code == 404


def test_malformed_job_id(client: TestClient) -> None:
    missing = client.get("/v1/jobs/not-a-job")
    assert missing.status_code == 404


def test_bearer_token_is_not_verified(client: TestClient) -> None:
    created = client.post(
        "/v1/jobs",
        headers={"Authorization": "Bearer not-a-real-jwt"},
        json={"filename": "clip.mp4"},
    )
    assert created.status_code == 202


def test_rejects_empty_filename(client: TestClient) -> None:
    rejected = client.post("/v1/jobs", json={"filename": ""})
    assert rejected.status_code == 422


def test_cors_allows_local_guardian(client: TestClient) -> None:
    response = client.options(
        "/v1/jobs",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
