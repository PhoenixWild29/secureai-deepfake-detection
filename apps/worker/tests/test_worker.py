import logging
import time
from pathlib import Path

import pytest

from detector import detect_video
from secureai_shared.models import JobStatus
from secureai_shared.report import load_report_detail
from secureai_shared.queue import MemoryJobQueue
from secureai_shared.storage import FileSystemStorage, new_object_key
from secureai_shared.store import PUBLIC_FAILURE_DETAIL, MemoryJobStore
from worker.__main__ import main, run
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


def test_process_job_stores_cpu_signals(tmp_path: Path) -> None:
    store, storage, job = _job(tmp_path)
    finished = process_job(
        store,
        storage,
        job.id,
        detect=lambda path: {
            "prediction": "fake",
            "confidence": 0.81,
            "model": "cpu-multisignal-v1",
            "signals": {"texture": 0.9, "motion": 0.2, "temporal": 0.4, "region": 0.0},
            "path": path,
        },
    )
    assert finished is not None
    model, signals = load_report_detail(finished.detail)
    assert model == "cpu-multisignal-v1"
    assert signals == {"texture": 0.9, "motion": 0.2, "temporal": 0.4, "region": 0.0}


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


def test_process_job_times_out_with_a_fixed_detail(
    tmp_path: Path,
    caplog: pytest.LogCaptureFixture,
) -> None:
    store, storage, job = _job(tmp_path)

    def hang(path: str) -> dict[str, object]:
        time.sleep(5)
        return {"prediction": "real", "confidence": 1, "path": path}

    with caplog.at_level(logging.ERROR, logger="secureai.worker"):
        finished = process_job(store, storage, job.id, detect=hang, timeout_seconds=0.2)
    assert finished is not None
    assert finished.status is JobStatus.failed
    assert finished.detail == PUBLIC_FAILURE_DETAIL
    assert str(tmp_path) not in caplog.text
    assert any("detector timed out" in record.message for record in caplog.records)


def test_process_job_rejects_a_changed_object(tmp_path: Path) -> None:
    store, storage, job = _job(tmp_path, b"clip-bytes")
    rewritten = store.get_any(job.id)
    assert rewritten is not None
    store._rows[job.id] = rewritten.model_copy(update={"object_etag": "not-the-file"})  # noqa: SLF001

    def explode(path: str) -> dict[str, object]:
        raise AssertionError(path)

    finished = process_job(store, storage, job.id, detect=explode)
    assert finished is not None
    assert finished.status is JobStatus.failed
    assert finished.detail == PUBLIC_FAILURE_DETAIL


def test_run_requeues_when_processing_raises(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("QUEUE_BACKEND", "memory")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    store = MemoryJobStore()
    queue = MemoryJobQueue()
    storage = FileSystemStorage(tmp_path)
    key = new_object_key("user_dev", "clip.mp4")
    storage.put(key, b"clip-bytes", "video/mp4")
    job = store.create(
        user_id="user_dev",
        filename="clip.mp4",
        content_type="video/mp4",
        byte_size=len(b"clip-bytes"),
        object_key=key,
    )
    queue.publish(job.id)
    monkeypatch.setattr("worker.__main__.PostgresJobStore", lambda url: store)
    monkeypatch.setattr("worker.__main__.build_queue", lambda settings: queue)
    monkeypatch.setattr("worker.__main__.build_storage", lambda settings: storage)

    def boom(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise RuntimeError("db down")

    monkeypatch.setattr("worker.__main__.process_job", boom)
    assert run(["--once"]) == 2
    assert queue.consume() == job.id


def test_run_once_enqueues_a_webhook_without_posting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("QUEUE_BACKEND", "memory")
    monkeypatch.delenv("REDIS_URL", raising=False)
    monkeypatch.setenv("STORAGE_BACKEND", "filesystem")
    monkeypatch.setenv("MEDIA_ROOT", str(tmp_path))
    store = MemoryJobStore()
    queue = MemoryJobQueue()
    storage = FileSystemStorage(tmp_path)
    org_id = "org_abcdef012345"
    key = new_object_key("user_dev", "clip.mp4")
    storage.put(key, b"clip-bytes", "video/mp4")
    job = store.create(
        user_id="user_dev",
        filename="clip.mp4",
        content_type="video/mp4",
        byte_size=len(b"clip-bytes"),
        object_key=key,
        org_id=org_id,
    )
    queue.publish(job.id)
    from secureai_shared.webhook_queue import MemoryWebhookQueue
    from secureai_shared.webhooks import MemoryWebhookStore

    webhooks = MemoryWebhookStore()
    webhooks.upsert_endpoint(
        org_id=org_id,
        url="https://customer.example/hooks/secureai",
        secret="signing-secret-value",
        keep_secret=False,
        notify_failures=True,
    )
    webhook_queue = MemoryWebhookQueue()
    monkeypatch.setattr("worker.__main__.PostgresJobStore", lambda url: store)
    monkeypatch.setattr("worker.__main__.build_queue", lambda settings: queue)
    monkeypatch.setattr("worker.__main__.build_storage", lambda settings: storage)
    monkeypatch.setattr("worker.__main__.open_webhook_store", lambda job_store: webhooks)
    monkeypatch.setattr("worker.__main__.build_webhook_queue", lambda settings: webhook_queue)

    def finish(job_store: MemoryJobStore, _storage: object, job_id: str, **_kwargs: object):
        claimed = job_store.claim(job_id)
        assert claimed is not None
        return job_store.complete(job_id, prediction="real", confidence=0.5, attempt=claimed.attempt)

    monkeypatch.setattr("worker.__main__.process_job", finish)
    assert run(["--once"]) == 0
    saved = webhooks.delivery_for_job(job.id)
    assert saved is not None
    assert saved.status == "pending"
    assert saved.attempt == 0
    assert webhook_queue.claim(now=saved.next_attempt_at.timestamp()) == saved.id


def test_missing_database_exits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    assert run(["--once"]) == 2


def test_main_flushes_error_reporting_before_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("worker.__main__.run", lambda **_kwargs: 7)
    flushed: list[str] = []
    monkeypatch.setattr("worker.__main__.flush_error_reporting", lambda: flushed.append("flushed"))
    with pytest.raises(SystemExit) as caught:
        main()
    assert caught.value.code == 7
    assert flushed == ["flushed"]


def test_main_flushes_error_reporting_when_run_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(**_kwargs: object) -> int:
        raise RuntimeError("queue down")

    monkeypatch.setattr("worker.__main__.run", boom)
    flushed: list[str] = []
    monkeypatch.setattr("worker.__main__.flush_error_reporting", lambda: flushed.append("flushed"))
    with pytest.raises(RuntimeError, match="queue down"):
        main()
    assert flushed == ["flushed"]


def test_worker_initializes_error_reporting_before_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    order: list[str] = []

    def load_settings(*args: object, **kwargs: object) -> object:
        del args, kwargs
        order.append("settings")

        class _Settings:
            database_url = "postgresql+psycopg://unused/unused"

        return _Settings()

    def init(settings: object, *, service: str) -> bool:
        del settings
        order.append(service)
        return False

    class Store:
        def __init__(self, url: str) -> None:
            del url
            order.append("store")
            raise RuntimeError("stop")

    monkeypatch.setattr("worker.__main__.load_settings", load_settings)
    monkeypatch.setattr("worker.__main__.init_error_reporting", init)
    monkeypatch.setattr("worker.__main__.PostgresJobStore", Store)
    assert run(["--once"]) == 2
    assert order == ["settings", "secureai-worker", "store"]
