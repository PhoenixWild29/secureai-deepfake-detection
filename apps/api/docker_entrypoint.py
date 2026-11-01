"""Replace this process with uvicorn so the API server is PID 1.

The image used to start ``sh -c`` so ``$PORT`` could expand. That shell is the
container's PID 1. It does not pass SIGTERM to uvicorn, and a shell that is
PID 1 ignores the signal, so the platform ends the container with SIGKILL.
``exec`` makes uvicorn the process that receives SIGTERM. Uvicorn then stops
accepting connections and drains in-flight requests.

``GET /health`` stays the liveness check. The Dockerfile HEALTHCHECK and the
Railway healthcheck both use that path.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping

# Bound a deploy so one stuck request cannot hold the old process open until
# the platform sends SIGKILL. In-flight work still gets this long to finish.
GRACEFUL_SHUTDOWN_SECONDS = 20


def listen_port(environ: Mapping[str, str]) -> str:
    """Return the TCP port uvicorn should bind.

    An empty ``PORT`` means 8000, which matches local ``docker run`` without
    Railway's injected value. A non-numeric value or a port outside 1–65535
    fails the process before it binds.
    """

    raw = environ.get("PORT", "").strip()
    if not raw:
        return "8000"
    if not raw.isascii() or not raw.isdigit():
        raise SystemExit("PORT must be a TCP port")
    port = int(raw)
    if port < 1 or port > 65535:
        raise SystemExit("PORT must be a TCP port")
    return str(port)


def uvicorn_argv(environ: Mapping[str, str]) -> list[str]:
    """Argv for ``os.execvp``. The first item is this interpreter."""

    return [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:create_app",
        "--factory",
        "--host",
        "0.0.0.0",
        "--port",
        listen_port(environ),
        "--timeout-graceful-shutdown",
        str(GRACEFUL_SHUTDOWN_SECONDS),
    ]


def main() -> None:
    argv = uvicorn_argv(os.environ)
    os.execvp(argv[0], argv)


if __name__ == "__main__":
    main()
