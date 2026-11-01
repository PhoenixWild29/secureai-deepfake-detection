"""The API image starts uvicorn as PID 1 and healthchecks GET /health."""

from __future__ import annotations

import os
import selectors
import signal
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from docker_entrypoint import (
    GRACEFUL_SHUTDOWN_SECONDS,
    listen_port,
    main,
    uvicorn_argv,
)

API_ROOT = Path(__file__).resolve().parents[1]


def test_listen_port_defaults_when_unset_or_blank() -> None:
    assert listen_port({}) == "8000"
    assert listen_port({"PORT": "  "}) == "8000"


def test_listen_port_normalizes_decimal_values() -> None:
    assert listen_port({"PORT": "8080"}) == "8080"
    assert listen_port({"PORT": "08080"}) == "8080"


@pytest.mark.parametrize("raw", ["0", "65536", "abc", "8000.1", "-1", "80 00", "８000"])
def test_listen_port_rejects_values_uvicorn_cannot_bind(raw: str) -> None:
    with pytest.raises(SystemExit, match="PORT must be a TCP port"):
        listen_port({"PORT": raw})


def test_uvicorn_argv_uses_the_factory_and_a_finite_drain() -> None:
    argv = uvicorn_argv({"PORT": "9000"})
    assert argv[0] == sys.executable
    assert argv[1:8] == [
        "-m",
        "uvicorn",
        "app.main:create_app",
        "--factory",
        "--host",
        "0.0.0.0",
        "--port",
    ]
    assert argv[8:] == ["9000", "--timeout-graceful-shutdown", str(GRACEFUL_SHUTDOWN_SECONDS)]


def test_main_replaces_this_process_with_uvicorn(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def fake_exec(file: str, args: list[str]) -> None:
        seen["file"] = file
        seen["args"] = args
        raise SystemExit(0)

    monkeypatch.setenv("PORT", "8123")
    monkeypatch.setattr(os, "execvp", fake_exec)
    with pytest.raises(SystemExit):
        main()
    assert seen["file"] == sys.executable
    assert seen["args"] == uvicorn_argv({"PORT": "8123"})


def test_exec_form_receives_sigterm() -> None:
    """SIGTERM is delivered to the process ``os.execvp`` installed.

    The entrypoint uses that replacement so uvicorn, not a parent shell, is
    the process the platform signals.
    """

    script = textwrap.dedent(
        """
        import os, sys
        os.execvp(
            sys.executable,
            [
                sys.executable,
                "-c",
                "import signal, sys; signal.signal(signal.SIGTERM, lambda *_: sys.exit(0)); print('ready', flush=True); signal.pause()",
            ],
        )
        """
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", script],
        start_new_session=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert proc.stdout is not None
        watcher = selectors.DefaultSelector()
        watcher.register(proc.stdout, selectors.EVENT_READ)
        assert watcher.select(timeout=2), "child did not become ready"
        assert proc.stdout.readline().strip() == "ready"
        proc.send_signal(signal.SIGTERM)
        assert proc.wait(timeout=2) == 0
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=2)


def test_dockerfile_execs_the_entrypoint_and_checks_public_health() -> None:
    text = (API_ROOT / "Dockerfile").read_text()
    cmd = next(line for line in text.splitlines() if line.startswith("CMD "))
    assert cmd == 'CMD ["python", "docker_entrypoint.py"]'
    assert "HEALTHCHECK" in text
    assert "/health" in text
    assert "/v1/admin/health" not in text
