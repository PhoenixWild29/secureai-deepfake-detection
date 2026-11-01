"""CPU multi-signal detector. No downloaded weights.

Each signal is between 0 and 1. Higher means the clip looks more synthetic
to this heuristic:

- texture: Laplacian energy. Flat frames score low. High-frequency noise scores high.
- motion: mean absolute change between sampled frames.
- temporal: histogram disagreement plus uneven motion (flicker). One frame scores 0.
- region: a face box from OpenCV's bundled Haar file when it loads, otherwise a
  skin-tone blob. The score rises when the border of that region is much
  sharper than the interior. No region scores 0. That is "no cue", not "real".

The mix is a fixed formula. It is not the legacy GPU ensemble and it has not
been measured on a labeled deepfake set. README.rebuild.md states that limit.
"""

from __future__ import annotations

import math
import os

from detector.stub import DetectionResult

CPU_MODEL = "cpu-multisignal-v1"
_SAMPLE_LIMIT = 8
_MAX_SIDE = 480
_WEIGHTS = {
    "texture": 0.42,
    "motion": 0.28,
    "temporal": 0.18,
    "region": 0.12,
}

_face_cascade: object | None = None
_face_ready = False


def detect_video_cpu(path: str) -> DetectionResult:
    import cv2

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
    scored = score_frames(frames)
    return {
        "prediction": scored["prediction"],
        "confidence": scored["confidence"],
        "model": CPU_MODEL,
        "signals": scored["signals"],
    }


def score_frames(frames: list[object]) -> DetectionResult:
    """Score BGR frames already in memory. Used by the file path and by tests."""

    import cv2
    import numpy as np

    prepared = [_fit(frame) for frame in frames]
    if not prepared:
        raise ValueError("video contains no readable frames")

    variances: list[float] = []
    motions: list[float] = []
    hist_distances: list[float] = []
    previous: object | None = None
    previous_hist: object | None = None
    for frame in prepared:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        variances.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
        current = gray.astype(np.float32)
        hist = _histogram(gray)
        if previous is not None and previous_hist is not None:
            motions.append(float(np.mean(np.abs(current - previous))))
            hist_distances.append(_histogram_distance(previous_hist, hist))
        previous = current
        previous_hist = hist

    mean_var = sum(variances) / len(variances)
    mean_motion = sum(motions) / len(motions) if motions else 0.0
    signals = {
        "texture": _texture(mean_var),
        "motion": _motion(mean_motion),
        "temporal": _temporal(motions, hist_distances),
        "region": _region(prepared),
    }
    probability = _combine(signals)
    prediction = "fake" if probability >= 0.5 else "real"
    confidence = round(max(probability, 1.0 - probability), 4)
    return {
        "prediction": prediction,
        "confidence": confidence,
        "model": CPU_MODEL,
        "signals": {name: round(value, 4) for name, value in signals.items()},
    }


def _fit(frame: object) -> object:
    import cv2

    height, width = frame.shape[:2]  # type: ignore[attr-defined]
    longest = max(height, width)
    if longest <= _MAX_SIDE:
        return frame
    scale = _MAX_SIDE / float(longest)
    return cv2.resize(
        frame,
        (max(1, int(width * scale)), max(1, int(height * scale))),
        interpolation=cv2.INTER_AREA,
    )


def _texture(mean_var: float) -> float:
    # Solid frames sit near 0. Random uint8 frames sit in the thousands.
    return _logistic((mean_var - 90.0) / 40.0)


def _motion(mean_motion: float) -> float:
    return _logistic((mean_motion - 8.0) / 4.0)


def _temporal(motions: list[float], hist_distances: list[float]) -> float:
    if not motions:
        return 0.0
    mean = sum(motions) / len(motions)
    variance = sum((item - mean) ** 2 for item in motions) / len(motions)
    spread = math.sqrt(variance)
    # A still clip has no flicker. A steady pan has motion but little spread.
    flicker = _logistic((spread - 4.0) / 2.0) if mean > 0.5 else 0.0
    histogram = sum(hist_distances) / len(hist_distances) if hist_distances else 0.0
    return _clamp(0.5 * flicker + 0.5 * histogram)


def _region(frames: list[object]) -> float:
    import cv2

    blends: list[float] = []
    centers: list[tuple[float, float]] = []
    for frame in frames:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mask = _region_mask(frame, gray)
        if mask is None:
            continue
        blends.append(_blend_mask(gray, mask))
        moment = cv2.moments(mask)
        if moment["m00"]:
            centers.append((moment["m10"] / moment["m00"], moment["m01"] / moment["m00"]))
    if not blends:
        return 0.0
    blend = sum(blends) / len(blends)
    jitter = _jitter(centers, frames[0].shape)  # type: ignore[attr-defined]
    return _clamp(0.75 * blend + 0.25 * jitter)


def _region_mask(frame: object, gray: object) -> object | None:
    import numpy as np

    faces = _face_boxes(gray)
    if faces:
        x, y, width, height = max(faces, key=lambda box: box[2] * box[3])
        mask = np.zeros(gray.shape[:2], dtype=np.uint8)  # type: ignore[attr-defined]
        mask[y : y + height, x : x + width] = 255
        return mask
    return _skin_mask(frame)


def _face_boxes(gray: object) -> list[tuple[int, int, int, int]]:
    cascade = _cascade()
    if cascade is None:
        return []
    found = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(24, 24))  # type: ignore[attr-defined]
    return [tuple(int(part) for part in box) for box in found]  # type: ignore[misc]


def _cascade() -> object | None:
    global _face_cascade, _face_ready
    if _face_ready:
        return _face_cascade
    _face_ready = True
    import cv2

    directory = getattr(cv2, "data", None)
    root = getattr(directory, "haarcascades", "")
    path = os.path.join(root, "haarcascade_frontalface_default.xml")
    if not root or not os.path.isfile(path):
        return None
    cascade = cv2.CascadeClassifier(path)
    if cascade.empty():
        return None
    _face_cascade = cascade
    return cascade


def _skin_mask(frame: object) -> object | None:
    """Largest skin-tone blob, when it covers enough of the frame to be a region."""

    import cv2
    import numpy as np

    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    mask = cv2.inRange(
        ycrcb,
        np.array([0, 133, 77], dtype=np.uint8),
        np.array([255, 173, 127], dtype=np.uint8),
    )
    kernel = np.ones((3, 3), dtype=np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    contours, _hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    contour = max(contours, key=cv2.contourArea)
    height, width = frame.shape[:2]  # type: ignore[attr-defined]
    if cv2.contourArea(contour) < 0.08 * height * width:
        return None
    filled = np.zeros(mask.shape, dtype=np.uint8)
    cv2.drawContours(filled, [contour], -1, 255, thickness=-1)
    return filled


def _blend_mask(gray: object, mask: object) -> float:
    """High when the seam around a region is much sharper than its interior.

    A soft boundary stays low. A noisy halo, including a hard pasted cutout,
    scores high. Real faces also have edges, so this cue is not proof.
    """

    import cv2
    import numpy as np

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    eroded = cv2.erode(mask, kernel)
    ring = cv2.subtract(cv2.dilate(mask, kernel), eroded)
    energy = np.abs(cv2.Laplacian(gray, cv2.CV_64F))
    interior = energy[eroded > 0]
    border = energy[ring > 0]
    if interior.size < 16 or border.size < 16:
        return 0.0
    ratio = float(border.mean()) / (float(interior.mean()) + 1.0)
    return _logistic((math.log1p(ratio) - 2.2) / 0.6)


def _jitter(centers: list[tuple[float, float]], shape: tuple[int, ...]) -> float:
    if len(centers) < 3:
        return 0.0
    height, width = shape[0], shape[1]
    diagonal = math.hypot(width, height) or 1.0
    jumps = [
        math.hypot(right[0] - left[0], right[1] - left[1]) / diagonal
        for left, right in zip(centers, centers[1:])
    ]
    mean_jump = sum(jumps) / len(jumps)
    return _logistic((mean_jump - 0.08) / 0.05)


def _histogram(gray: object) -> object:
    import cv2
    import numpy as np

    hist = cv2.calcHist([gray], [0], None, [16], [0, 256]).astype(np.float64).reshape(-1)
    total = float(hist.sum())
    if total <= 0.0:
        return hist
    return hist / total


def _histogram_distance(left: object, right: object) -> float:
    import numpy as np

    overlap = float(np.sum(np.sqrt(left * right)))  # type: ignore[operator]
    return _clamp(1.0 - overlap)


def _combine(signals: dict[str, float]) -> float:
    return _clamp(sum(_WEIGHTS[name] * signals[name] for name in _WEIGHTS))


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


def _clamp(value: float) -> float:
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value
