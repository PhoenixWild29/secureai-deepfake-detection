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
import time
from pathlib import Path

from secureai_shared.queue import build_queue
from secureai_shared.settings import load_settings
from secureai_shared.storage import build_storage, new_object_key
from secureai_shared.store import PostgresJobStore
from worker.consumer import process_job

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
    except Exception:
        logger.exception("worker configuration failed")
        return 2

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

    announced_idle = False
    while not stop["flag"]:
        try:
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
        process_job(store, storage, job_id)
        if args.once:
            return 0
        if args.poll_seconds <= 0:
            time.sleep(0.1)
    return 0


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
