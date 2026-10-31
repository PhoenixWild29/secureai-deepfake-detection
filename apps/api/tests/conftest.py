from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.settings import Settings
from secureai_shared.storage import FileSystemStorage
from secureai_shared.store import MemoryJobStore


def make_settings(tmp_path: Path, **overrides: object) -> Settings:
    values: dict[str, object] = {
        "auth_mode": "dev",
        "clerk_issuer": "",
        "clerk_jwks_url": "",
        "clerk_authorized_parties": (),
        "database_url": "postgresql+psycopg://unused/unused",
        "redis_url": "",
        "queue_backend": "memory",
        "queue_key": "secureai:jobs",
        "storage_backend": "filesystem",
        "media_root": str(tmp_path),
        "s3_endpoint": "",
        "s3_bucket": "",
        "s3_access_key_id": "",
        "s3_secret_access_key": "",
        "s3_region": "us-east-1",
        "cors_origins": ("http://localhost:3000",),
        "dev_subject": "user_dev",
        "max_upload_bytes": 50_000_000,
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


def _client(tmp_path: Path, settings: Settings):
    store = MemoryJobStore()
    queue = MemoryJobQueue()
    storage = FileSystemStorage(tmp_path)
    app = create_app(settings=settings, store=store, queue=queue, storage=storage)
    return TestClient(app), store, queue, storage


@pytest.fixture
def stack(tmp_path: Path):
    client, store, queue, storage = _client(tmp_path, make_settings(tmp_path))
    with client:
        yield client, store, queue, storage


@pytest.fixture
def limited_client(tmp_path: Path):
    client, _, _, _ = _client(tmp_path, make_settings(tmp_path, max_upload_bytes=4))
    with client:
        yield client
