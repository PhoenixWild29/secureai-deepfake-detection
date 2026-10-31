from pathlib import Path

import cv2
import numpy as np

from detector import detect_video


def _write(path: Path, kind: str) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"MJPG"), 8, (64, 64))
    assert writer.isOpened()
    rng = np.random.default_rng(1)
    for _ in range(8):
        if kind == "flat":
            frame = np.full((64, 64, 3), 128, dtype=np.uint8)
        else:
            frame = rng.integers(0, 256, (64, 64, 3), dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_cpu_scores_flat_and_noisy_clips_differently(tmp_path: Path) -> None:
    flat = tmp_path / "flat.avi"
    noisy = tmp_path / "noisy.avi"
    _write(flat, "flat")
    _write(noisy, "noisy")

    flat_result = detect_video(str(flat), mode="cpu")
    noisy_result = detect_video(str(noisy), mode="cpu")

    assert flat_result["prediction"] in {"real", "fake"}
    assert noisy_result["prediction"] in {"real", "fake"}
    assert 0.0 <= float(flat_result["confidence"]) <= 1.0
    assert 0.0 <= float(noisy_result["confidence"]) <= 1.0
    assert flat_result != noisy_result
    assert flat_result["prediction"] == "real"
    assert noisy_result["prediction"] == "fake"


def test_cpu_missing_file_raises(tmp_path: Path) -> None:
    missing = tmp_path / "missing.avi"
    try:
        detect_video(str(missing), mode="cpu")
    except FileNotFoundError:
        return
    raise AssertionError("expected FileNotFoundError")
