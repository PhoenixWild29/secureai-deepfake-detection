"""Deterministic hash scorer. Does not read media or load weights.

DETECTOR_MODE=stub keeps CI and unit tests off OpenCV. The default path is
the CPU sampler in detector.cpu.
"""

from __future__ import annotations

import hashlib
from typing import Literal, TypedDict


class DetectionResult(TypedDict):
    prediction: Literal["real", "fake"]
    confidence: float


def detect_video_stub(path: str) -> DetectionResult:
    """Return a stable score for `path`. The file does not need to exist."""

    digest = hashlib.sha256(path.encode("utf-8")).digest()
    confidence = round(0.5 + (digest[0] / 255) * 0.49, 4)
    prediction: Literal["real", "fake"] = "fake" if digest[1] % 2 else "real"
    return {"prediction": prediction, "confidence": confidence}
