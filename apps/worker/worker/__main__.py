"""Poll the Phase 0 in-memory queue.

    python -m worker --demo --once
    python -m worker

QUEUE_BACKEND defaults to memory. QUEUE_BACKEND=redis exits with an error
until Phase 1 connects Redis. The long-running process does not see jobs
created in the API process.
"""

from __future__ import annotations

import argparse
import logging
import signal
import time

from secureai_shared.queue import MemoryJobQueue, build_queue
from worker.consumer import process_next

logger = logging.getLogger("secureai.worker")


def run(argv: list[str] | None = None, *, install_signal_handlers: bool = False) -> int:
    parser = argparse.ArgumentParser(description="SecureAI CPU worker (Phase 0 stub)")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process at most one job, then exit",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Enqueue a synthetic job on this process's queue before polling",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=2.0,
        help="Sleep between empty polls (long-running mode)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")

    try:
        queue = build_queue()
    except NotImplementedError as exc:
        logger.error("%s", exc)
        return 2
    except ValueError as exc:
        logger.error("%s", exc)
        return 2

    if args.demo:
        if not isinstance(queue, MemoryJobQueue):
            logger.error("--demo requires the in-memory queue")
            return 2
        queue.enqueue(filename="demo-clip.mp4", content_type="video/mp4", byte_size=0)

    stop = {"flag": False}

    def request_stop(signum: int, _frame: object) -> None:
        logger.info("shutdown signal=%s", signum)
        stop["flag"] = True

    if install_signal_handlers:
        signal.signal(signal.SIGTERM, request_stop)
        signal.signal(signal.SIGINT, request_stop)

    announced_idle = False
    while not stop["flag"]:
        job = process_next(queue)
        if job is not None:
            announced_idle = False
            if args.once:
                return 0
            continue
        if args.once:
            logger.info("no queued jobs")
            return 0
        if not announced_idle:
            logger.info(
                "idle: this process-local queue is empty. API jobs are not "
                "visible until Phase 1 connects Redis."
            )
            announced_idle = True
        time.sleep(args.poll_seconds)
    return 0


def main() -> None:
    raise SystemExit(run(install_signal_handlers=True))


if __name__ == "__main__":
    main()
