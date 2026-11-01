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
import math
import signal
import tempfile
import threading
import time
from pathlib import Path

from secureai_shared.models import JobRecord
from secureai_shared.queue import build_queue
from secureai_shared.reporting import flush_error_reporting, init_error_reporting, install_error_log_redaction
from secureai_shared.settings import Settings, load_settings
from secureai_shared.storage import build_storage, new_object_key
from secureai_shared.store import PostgresJobStore
from secureai_shared.webhook_queue import WebhookQueue, build_webhook_queue
from secureai_shared.webhooks import WebhookStore, deliver_once, open_webhook_store, post_webhook, schedule_terminal
from worker.consumer import process_job
from worker.recovery import rescue_popped, sweep_stuck

logger = logging.getLogger("secureai.worker")

# argparse default. The Redis wait uses this unless the process is started
# with --poll-seconds. Railway uses the image command, so it is 5.
DEFAULT_POLL_SECONDS = 5.0
# main() calls flush_error_reporting() with no arguments.
SENTRY_FLUSH_SECONDS = 2.0
# Claim, object download, and the row write are outside the detector timer.
DRAIN_MARGIN_SECONDS = 8.0
# post_webhook can spend the timeout on TCP, then the same timeout again
# on TLS and the HTTP response. These seconds cover the delivery row write.
WEBHOOK_JOIN_MARGIN_SECONDS = 2.0


def shutdown_drain_seconds() -> int:
    """Seconds the platform must wait after SIGTERM before SIGKILL.

    The handler only sets a flag. ``run`` reads that flag after the current
    Redis wait and after the job that wait already popped. It then joins
    the webhook POST already in progress. ``main`` flushes error reporting.
    A shorter drain ends the process with SIGKILL and leaves that job leased
    until ``STUCK_JOB_SECONDS``.

    The sum uses the default poll, the default detector timeout, and the
    default Sentry flush. It does not read ``DETECTOR_TIMEOUT_SECONDS``.
    A larger timeout needs a larger platform drain. ``run`` warns once at
    startup when the configured timeout is greater than this default.

    Keep the webhook join out of this sum. The POST runs while a popped job
    is scored, and an idle shutdown is the poll plus
    ``webhook_shutdown_join_seconds`` plus the Sentry flush. Both fit here
    for the default webhook timeout and for the maximum of 30 seconds.
    """

    total = (
        DEFAULT_POLL_SECONDS
        + Settings.detector_timeout_seconds
        + SENTRY_FLUSH_SECONDS
        + DRAIN_MARGIN_SECONDS
    )
    return math.ceil(total)


def webhook_shutdown_join_seconds(timeout_seconds: float) -> float:
    """How long shutdown waits for the webhook POST already in progress.

    ``post_webhook`` uses ``timeout_seconds`` once for every TCP attempt,
    then sets the socket timeout back to that same value for TLS and the
    response. The margin covers the row write after the socket returns.
    The join is bounded so a hung DNS lookup still lets ``main`` flush Sentry.
    """

    return timeout_seconds * 2 + WEBHOOK_JOIN_MARGIN_SECONDS


def warn_if_detector_timeout_exceeds_drain(timeout_seconds: float) -> None:
    """Warn when the env timeout is longer than the platform drain budget.

    ``shutdown_drain_seconds`` and ``deploy/railway/worker.railway.json`` stay
    on the default detector timeout (60). Raising ``DETECTOR_TIMEOUT_SECONDS``
    without raising ``drainingSeconds`` by the same amount lets Railway
    SIGKILL a job that is still inside ``detect_video``.
    """

    default_timeout = Settings.detector_timeout_seconds
    if timeout_seconds <= default_timeout:
        return
    delta = timeout_seconds - default_timeout
    logger.warning(
        "DETECTOR_TIMEOUT_SECONDS=%g is greater than the default %g tracked by "
        "shutdown_drain_seconds() (drainingSeconds=%s). The drain budget may be "
        "short. Raise drainingSeconds by %g.",
        timeout_seconds,
        default_timeout,
        shutdown_drain_seconds(),
        delta,
    )


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
        default=DEFAULT_POLL_SECONDS,
        help="BRPOP timeout between empty reads",
    )
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    # Handler filters cover library WARNING and ERROR logs that propagate to
    # the root handler, including a presigned URL inside a storage exception.
    # Logger filters do not run for those propagated records.
    install_error_log_redaction(logging.getLogger())

    try:
        settings = load_settings(role="worker")
        init_error_reporting(settings, service="secureai-worker")
        store = PostgresJobStore(settings.database_url)
        queue = build_queue(settings)
        storage = build_storage(settings)
        webhooks = open_webhook_store(store)
        webhook_queue = build_webhook_queue(settings)
    except Exception:
        logger.exception("worker configuration failed")
        return 2

    # Once, before the poll loop. The drain budget does not follow the env.
    warn_if_detector_timeout_exceeds_drain(settings.detector_timeout_seconds)

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
        # A flag, not SystemExit. Raising here would drop the id this process
        # already popped and leave its lease until STUCK_JOB_SECONDS. The
        # loop scores that job, then returns. The webhook thread is joined
        # before that return. shutdown_drain_seconds() is how long the
        # platform has to wait before SIGKILL.
        logger.info("shutdown signal=%s", signum)
        stop["flag"] = True

    if install_signal_handlers:
        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)

    # Daemon so a join that hits its limit can still return and flush Sentry.
    # A non-daemon thread would keep the process up after that limit.
    webhook_thread: threading.Thread | None = None
    try:
        if not args.once:
            webhook_thread = threading.Thread(
                target=_serve_webhooks,
                name="secureai-webhooks",
                args=(stop, webhooks, webhook_queue, settings),
                daemon=True,
            )
            webhook_thread.start()

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
    finally:
        _join_webhook_thread(webhook_thread, stop, settings.webhook_timeout_seconds)


def _join_webhook_thread(
    thread: threading.Thread | None,
    stop: dict[str, bool],
    timeout_seconds: float,
) -> None:
    """Finish the POST already claimed, then let the process exit.

    The flag stops the thread from claiming another id. The join covers
    the POST ``deliver_once`` is already inside. A thread that was never
    started (tests replace ``Thread.start``) is left alone.
    """

    stop["flag"] = True
    if thread is None or not thread.is_alive():
        return
    join_for = webhook_shutdown_join_seconds(timeout_seconds)
    logger.info("shutdown finishing in-flight webhook delivery (join %gs)", join_for)
    thread.join(timeout=join_for)
    if thread.is_alive():
        logger.warning(
            "in-flight webhook delivery did not finish within %gs of shutdown; "
            "the claim lease is the retry",
            join_for,
        )


def _serve_webhooks(
    stop: dict[str, bool],
    webhooks: WebhookStore,
    webhook_queue: WebhookQueue,
    settings: Settings,
) -> None:
    """POST due deliveries. This thread is the only place the worker does webhook I/O.

    ``run`` sets the stop flag and joins this thread on the way out. The
    flag is read between deliveries, so the POST already inside
    ``deliver_once`` can store its result, and the next id stays queued.
    """

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
    code = 1
    try:
        code = run(install_signal_handlers=True)
    finally:
        # LoggingIntegration queues ERROR records on a daemon thread.
        # Flush before SystemExit so a configuration failure or --once
        # job is not dropped when the process ends.
        flush_error_reporting()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
