import logging
from pathlib import Path

import pytest

from detector import detect_video
from secureai_shared.models import JobStatus
from secureai_shared.storage import FileSystemStorage, new_object_key
from secureai_shared.store import PUBLIC_FAILURE_DETAIL, MemoryJobStore
from worker.__main__ import run
from worker.consumer import process_job


def _job(tmp_path: Path, payload: bytes = b"clip-bytes"):
    store = MemoryJobStore()
    storage = FileSystemStorage(tmp_path)
    key = new_object_key("user_dev", "clip.mp4")
    storage.put(key, payload, "video/mp4")
    job = store.create(
        user_id="user_dev",
        filename="clip.mp4",
        content_type="video/mp4",
        byte_size=len(payload),
        object_key=key,
    )
    return store, storage, job


def test_process_job_completes_with_stub(tmp_path: Path) -> None:
    store, storage, job = _job(tmp_path)
    finished = process_job(
        store,
        storage,
        job.id,
        detect=lambda path: detect_video(path, mode="stub"),
    )
    assert finished is not None
    assert finished.status is JobStatus.completed
    assert finished.prediction in {"real", "fake"}
    assert finished.confidence is not None
    assert finished.detail is None
    assert store.get(job.id, user_id="user_dev") == finished


def test_process_job_stores_a_fixed_failure_detail(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    store, storage, job = _job(tmp_path)

    def explode(path: str) -> dict[str, object]:
        raise RuntimeError(f"secret path {path}")

    with caplog.at_level(logging.ERROR, logger="secureai.worker"):
        finished = process_job(store, storage, job.id, detect=explode)
    assert finished is not None
    assert finished.detail == PUBLIC_FAILURE_DETAIL
    assert "secret path" not in (finished.detail or "")
    assert any(
        record.exc_info is not None and "secret path" in str(record.exc_info[1])
        for record in caplog.records
    )


def test_process_job_on_unknown_id(tmp_path: Path) -> None:
    store = MemoryJobStore()
    storage = FileSystemStorage(tmp_path)
    assert process_job(store, storage, "job_0123456789ab") is None


def test_missing_database_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    assert run(["--once"]) == 2
