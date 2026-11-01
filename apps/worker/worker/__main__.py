"""Poll the shared Redis queue and score jobs.

    python -m worker
    python -m worker --once
    python -m worker --demo --once

Start the API first so Alembic has created the jobs table. --demo writes a
short clip, stores it, and publishes one job for user_demo.
"""

from __future__ import annotations

import argparse
import logging
import signal
import tempfile
import threading
import time
from pathlib import Path

from secureai_shared.models import JobRecord
from secureai_shared.queue import build_queue
from secureai_shared.settings import Settings, load_settings
from secureai_shared.storage import build_storage, new_object_key
from secureai_shared.store import PostgresJobStore
from secureai_shared.webhook_queue import WebhookQueue, build_webhook_queue
from secureai_shared.webhooks import WebhookStore, deliver_once, open_webhook_store, post_webhook, schedule_terminal
from worker.consumer import process_job
from worker.recovery import rescue_popped, sweep_stuck

logger = logging.getLogger("secureai.worker")


def run(argv: list[str] | None = None, *, install_signal_handlers: bool = False) -> int:
    parser = argparse.ArgumentParser(description="SecureAI CPU detection worker")
    parser.add_argument("--once", action="store_true", help="Process at most one job, then exit")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Store a tiny generated clip and publish it before polling",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=5.0,
        help="BRPOP timeout between empty reads",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    try:
        settings = load_settings(role="worker")
        store = PostgresJobStore(settings.database_url)
        queue = build_queue(settings)
        storage = build_storage(settings)
        webhooks = open_webhook_store(store)
        webhook_queue = build_webhook_queue(settings)
    except Exception:
        logger.exception("worker configuration failed")
        return 2

    def note_terminal(job: JobRecord) -> None:
        try:
            schedule_terminal(webhooks, webhook_queue, job)
        except Exception:
            logger.exception("webhook schedule failed job_id=%s", job.id)

    if args.demo:
        try:
            _publish_demo(store, queue, storage)
        except Exception:
            logger.exception("demo job failed")
            return 2

    stop = {"flag": False}

    def request_stop(signum: int, _frame: object) -> None:
        logger.info("shutdown signal=%s", signum)
        stop["flag"] = True

    if install_signal_handlers:
        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)

    if not args.once:
        threading.Thread(
            target=_serve_webhooks,
            name="secureai-webhooks",
            args=(stop, webhooks, webhook_queue, settings),
            daemon=True,
        ).start()

    announced_idle = False
    while not stop["flag"]:
        try:
            sweep_stuck(
                store,
                queue,
                lease_seconds=settings.stuck_job_seconds,
                max_attempts=settings.job_max_attempts,
                on_terminal=note_terminal,
            )
            job_id = queue.consume(timeout=0 if args.once else args.poll_seconds)
        except Exception:
            logger.exception("queue read failed")
            return 2
        if job_id is None:
            if args.once:
                logger.info("no queued jobs")
                return 0
            if not announced_idle:
                logger.info("idle: waiting for job ids on %s", settings.queue_key)
                announced_idle = True
            continue
        announced_idle = False
        try:
            finished = process_job(
                store,
                storage,
                job_id,
                timeout_seconds=settings.detector_timeout_seconds,
                max_upload_bytes=settings.max_upload_bytes,
            )
        except Exception:
            logger.exception("job aborted job_id=%s", job_id)
            try:
                rescue_popped(store, queue, job_id, on_terminal=note_terminal)
            except Exception:
                logger.exception("could not rescue job_id=%s", job_id)
            return 2
        if finished is None:
            logger.info("job not owned after pop job_id=%s", job_id)
        else:
            note_terminal(finished)
        # Drop only the lease this pop created. A newer claim keeps its lease.
        queue.ack(job_id, attempt=queue.held_attempt(job_id))
        if args.once:
            return 0
        if args.poll_seconds <= 0:
            time.sleep(0.1)
    return 0


def _serve_webhooks(
    stop: dict[str, bool],
    webhooks: WebhookStore,
    webhook_queue: WebhookQueue,
    settings: Settings,
) -> None:
    """POST due deliveries. This thread is the only place the worker does webhook I/O."""

    while not stop["flag"]:
        try:
            worked = deliver_once(
                webhooks,
                webhook_queue,
                post=post_webhook,
                timeout=settings.webhook_timeout_seconds,
                max_attempts=settings.webhook_max_attempts,
                lease_seconds=settings.webhook_timeout_seconds + 15,
            )
        except Exception:
            logger.exception("webhook delivery error")
            worked = False
        if worked:
            continue
        for _ in range(10):
            if stop["flag"]:
                return
            time.sleep(0.1)


def _publish_demo(store: PostgresJobStore, queue: object, storage: object) -> None:
    import cv2
    import numpy as np

    handle = tempfile.NamedTemporaryFile(suffix=".avi", delete=False)
    handle.close()
    path = Path(handle.name)
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 8, (64, 64))
    if not writer.isOpened():
        path.unlink(missing_ok=True)
        raise RuntimeError("could not write the demo clip")
    frame = np.full((64, 64, 3), 32, dtype=np.uint8)
    for _ in range(6):
        writer.write(frame)
    writer.release()
    data = path.read_bytes()
    path.unlink(missing_ok=True)

    key = new_object_key("user_demo", "demo.avi")
    storage.put(key, data, "video/x-msvideo")  # type: ignore[attr-defined]
    job = store.create(
        user_id="user_demo",
        filename="demo.avi",
        content_type="video/x-msvideo",
        byte_size=len(data),
        object_key=key,
    )
    queue.publish(job.id)  # type: ignore[attr-defined]
    logger.info("demo queued job_id=%s", job.id)


def main() -> None:
    raise SystemExit(run(install_signal_handlers=True))


if __name__ == "__main__":
    main()
