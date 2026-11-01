from pathlib import Path

import cv2
import numpy as np

from detector import detect_video
from detector.cpu import score_frames


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


def test_cpu_reports_bounded_signals(tmp_path: Path) -> None:
    flat = tmp_path / "flat.avi"
    noisy = tmp_path / "noisy.avi"
    _write(flat, "flat")
    _write(noisy, "noisy")
    flat_result = detect_video(str(flat), mode="cpu")
    noisy_result = detect_video(str(noisy), mode="cpu")

    assert flat_result["model"] == "cpu-multisignal-v1"
    assert set(flat_result["signals"]) == {"texture", "motion", "temporal", "region"}
    for result in (flat_result, noisy_result):
        for value in result["signals"].values():
            assert 0.0 <= float(value) <= 1.0
    assert float(noisy_result["signals"]["texture"]) > float(flat_result["signals"]["texture"])
    assert float(noisy_result["signals"]["temporal"]) > float(flat_result["signals"]["temporal"])
    assert float(flat_result["signals"]["region"]) == 0.0


def test_region_cue_rises_when_a_border_is_sharper_than_the_interior() -> None:
    calm = [_skin_disc(noise_ring=False) for _ in range(4)]
    cutout = [_skin_disc(noise_ring=True) for _ in range(4)]
    calm_score = score_frames(calm)
    cutout_score = score_frames(cutout)
    assert float(cutout_score["signals"]["region"]) > float(calm_score["signals"]["region"])
    assert float(cutout_score["signals"]["region"]) > 0.5


def _skin_disc(*, noise_ring: bool) -> np.ndarray:
    """A soft skin-colored disc. The ring variant adds a noisy halo on the seam."""

    frame = np.full((96, 96, 3), (40, 90, 30), dtype=np.uint8)
    yy, xx = np.ogrid[:96, :96]
    distance = np.sqrt((yy - 48) ** 2 + (xx - 48) ** 2)
    skin = np.array([120, 160, 210], dtype=np.float32)
    alpha = np.clip((34.0 - distance) / 10.0, 0.0, 1.0)[..., None]
    mixed = frame.astype(np.float32) * (1.0 - alpha) + skin * alpha
    frame = mixed.astype(np.uint8)
    if noise_ring:
        ring = (distance > 26) & (distance <= 36)
        rng = np.random.default_rng(2)
        frame[ring] = rng.integers(0, 256, (int(ring.sum()), 3), dtype=np.uint8)
    return frame
