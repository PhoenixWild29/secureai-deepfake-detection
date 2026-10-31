"""Deterministic CPU stub. Does not read media or load model weights.

TODO(phase-1): replace detect_video with the real CPU ensemble. Keep this
module free of GPU-only imports. The worker will pass an object-storage
download path instead of a filename token.
"""

from __future__ import annotations

import hashlib
from typing import Literal, TypedDict


class DetectionResult(TypedDict):
    prediction: Literal["real", "fake"]
    confidence: float


def detect_video(path: str) -> DetectionResult:
    """Return a stable fake score for `path`.

    The file does not need to exist. The score is a hash of the path so tests
    and the worker demo stay repeatable without datasets or weights.
    """

    digest = hashlib.sha256(path.encode("utf-8")).digest()
    confidence = round(0.5 + (digest[0] / 255) * 0.49, 4)
    prediction: Literal["real", "fake"] = "fake" if digest[1] % 2 else "real"
    return {"prediction": prediction, "confidence": confidence}
