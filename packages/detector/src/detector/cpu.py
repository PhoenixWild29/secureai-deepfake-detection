"""Small CPU detector. Samples frames and scores texture plus motion.

This is a lightweight baseline so a worker can score a short clip without a
GPU. It is not the legacy ensemble and it does not download weights.
"""

from __future__ import annotations

import math

from detector.stub import DetectionResult

_SAMPLE_LIMIT = 8


def detect_video_cpu(path: str) -> DetectionResult:
    import cv2
    import numpy as np

    capture = cv2.VideoCapture(path)
    if not capture.isOpened():
        raise FileNotFoundError(path)
    try:
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frames = _read_samples(capture, total)
    finally:
        capture.release()
    if not frames:
        raise ValueError("video contains no readable frames")

    variances: list[float] = []
    motions: list[float] = []
    previous = None
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        variances.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
        current = gray.astype(np.float32)
        if previous is not None:
            motions.append(float(np.mean(np.abs(current - previous))))
        previous = current

    mean_var = sum(variances) / len(variances)
    mean_motion = sum(motions) / len(motions) if motions else 0.0
    # Flat clips sit below 0.5. High-frequency noise pushes the score up.
    prob_fake = _logistic(-1.8 + 0.012 * mean_var + 0.03 * mean_motion)
    prediction = "fake" if prob_fake >= 0.5 else "real"
    confidence = round(max(prob_fake, 1.0 - prob_fake), 4)
    return {"prediction": prediction, "confidence": confidence}


def _read_samples(capture: object, total: int) -> list[object]:
    import cv2

    frames: list[object] = []
    positions = _positions(total)
    if positions:
        for index in positions:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)  # type: ignore[attr-defined]
            ok, frame = capture.read()  # type: ignore[attr-defined]
            if ok and frame is not None:
                frames.append(frame)
        if frames:
            return frames
    for _ in range(_SAMPLE_LIMIT):
        ok, frame = capture.read()  # type: ignore[attr-defined]
        if not ok or frame is None:
            break
        frames.append(frame)
    return frames


def _positions(total: int) -> list[int]:
    if total <= 0:
        return []
    if total <= _SAMPLE_LIMIT:
        return list(range(total))
    step = (total - 1) / (_SAMPLE_LIMIT - 1)
    return [int(round(step * index)) for index in range(_SAMPLE_LIMIT)]


def _logistic(value: float) -> float:
    if value > 20:
        value = 20
    if value < -20:
        value = -20
    return 1.0 / (1.0 + math.exp(-value))
