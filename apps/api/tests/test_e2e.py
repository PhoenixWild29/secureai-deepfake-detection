"""API, Redis, Postgres, and the worker process share one job."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import create_app

REDIS_URL = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/0")
DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+psycopg://secureai:secureai@127.0.0.1:5432/secureai",
)
QUEUE_KEY = "secureai:jobs:e2e"


def _services_available() -> bool:
    try:
        import psycopg
        import redis

        redis.Redis.from_url(REDIS_URL, decode_responses=True).ping()
        with psycopg.connect(DATABASE_URL.replace("postgresql+psycopg://", "postgresql://", 1)) as conn:
            conn.execute("SELECT 1")
    except Exception:
        return False
    return True


pytestmark = pytest.mark.skipif(not _services_available(), reason="redis or postgres unavailable")


def _clip() -> bytes:
    path = Path("/tmp/secureai-e2e-clip.avi")
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 8, (64, 64))
    assert writer.isOpened()
    rng = np.random.default_rng(3)
    for _ in range(6):
        writer.write(rng.integers(0, 256, (64, 64, 3), dtype=np.uint8))
    writer.release()
    data = path.read_bytes()
    path.unlink(missing_ok=True)
    return data


def test_worker_completes_a_queued_upload(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import redis

    client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    client.delete(QUEUE_KEY)
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DEV_AUTH_SUBJECT", "user_e2e")
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    monkeypatch.setenv("REDIS_URL", REDIS_URL)
    monkeypatch.setenv("QUEUE_BACKEND", "redis")
    monkeypatch.setenv("QUEUE_KEY", QUEUE_KEY)
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    monkeypatch.setenv("DETECTOR_MODE", "cpu")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000")

    with TestClient(create_app()) as api:
        anonymous = api.post("/v1/uploads", json={"filename": "clip.avi"})
        assert anonymous.status_code == 401
        headers = {"Authorization": "Bearer dev"}
        uploaded = api.post(
            "/v1/media",
            headers=headers,
            files={"file": ("clip.avi", _clip(), "video/x-msvideo")},
        )
        assert uploaded.status_code == 200
        media = uploaded.json()
        created = api.post(
            "/v1/jobs",
            headers=headers,
            json={
                "object_key": media["object_key"],
                "filename": media["filename"],
                "content_type": media["content_type"],
                "byte_size": media["byte_size"],
            },
        )
        assert created.status_code == 202
        job_id = created.json()["id"]

        root = Path(__file__).resolve().parents[3]
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            [
                str(root / "apps" / "worker"),
                str(root / "packages" / "shared" / "src"),
                str(root / "packages" / "detector" / "src"),
                env.get("PYTHONPATH", ""),
            ]
        )
        completed = subprocess.run(
            [sys.executable, "-m", "worker", "--once"],
            cwd=str(root),
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        fetched = api.get(f"/v1/jobs/{job_id}", headers=headers)
        assert fetched.status_code == 200
        body = fetched.json()
        assert body["status"] == "completed"
        assert body["prediction"] in {"real", "fake"}
        assert 0.0 <= body["confidence"] <= 1.0
        assert body["detail"] is None
    client.delete(QUEUE_KEY)
