"""Run detection in a child process so a hung call can be stopped."""

from __future__ import annotations

import threading


class DetectionTimeout(Exception):
    """The detector did not finish inside the allowed time."""


def call_detect(detect, path: str, timeout: float, *, isolate: bool) -> dict[str, object]:
    if isolate:
        return _run_process(path, timeout)
    return _run_thread(detect, path, timeout)


def _run_thread(detect, path: str, timeout: float) -> dict[str, object]:
    box: dict[str, object] = {}

    def target() -> None:
        try:
            box["result"] = detect(path)
        except Exception as exc:
            box["error"] = exc

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise DetectionTimeout()
    if "error" in box:
        raise box["error"]  # type: ignore[misc]
    result = box.get("result")
    if not isinstance(result, dict):
        raise RuntimeError("detector returned nothing")
    return result


def _detect_child(conn: object, path: str) -> None:
    try:
        from detector import detect_video

        conn.send(("ok", detect_video(path)))  # type: ignore[attr-defined]
    except Exception as exc:
        conn.send(("err", type(exc).__name__))  # type: ignore[attr-defined]
    finally:
        conn.close()  # type: ignore[attr-defined]


def _run_process(path: str, timeout: float) -> dict[str, object]:
    import multiprocessing as mp

    ctx = mp.get_context("spawn")
    parent, child = ctx.Pipe(duplex=False)
    proc = ctx.Process(target=_detect_child, args=(child, path))
    proc.start()
    child.close()
    proc.join(timeout)
    if proc.is_alive():
        proc.terminate()
        proc.join(2)
        if proc.is_alive():
            proc.kill()
            proc.join(1)
        parent.close()
        raise DetectionTimeout()
    if not parent.poll(1):
        parent.close()
        raise RuntimeError("detector process returned nothing")
    kind, payload = parent.recv()
    parent.close()
    if kind != "ok" or not isinstance(payload, dict):
        raise RuntimeError("detector process failed")
    return payload
