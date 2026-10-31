"""Public detection API.

DETECTOR_MODE=cpu (default) samples frames on CPU.
DETECTOR_MODE=stub hashes the path and does not open the file.
"""

from __future__ import annotations

import os

from detector.cpu import detect_video_cpu
from detector.stub import detect_video_stub

__all__ = ["detect_video"]


def detect_video(path: str, mode: str | None = None) -> dict[str, object]:
    selected = mode if mode is not None else os.environ.get("DETECTOR_MODE", "cpu")
    selected = (selected or "cpu").strip().lower()
    if selected == "stub":
        return detect_video_stub(path)
    if selected == "cpu":
        return detect_video_cpu(path)
    raise ValueError(
        f"Unknown DETECTOR_MODE {selected!r}. Use 'cpu' or 'stub'."
    )
