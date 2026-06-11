"""Aligned face-crop extraction from videos or frame folders.

This is P0.1 in MODEL_IMPROVEMENT_PLAN.md — "the single biggest lever". Every
strong deepfake detector operates on detected, aligned face crops, not full
frames. We extract crops here so train and inference see the same distribution.

Primary detector: facenet-pytorch MTCNN (fast, gives 5-point landmarks we can
use for alignment). Fallback: OpenCV Haar cascade (no landmarks; center-crop
alignment) so the pipeline still runs if facenet-pytorch is unavailable.

All heavy imports (cv2, numpy, torch, facenet_pytorch) are done lazily inside
functions so this module imports cleanly in a torch-free sandbox.

Functions
---------
extract_faces_from_video(video_path, out_dir, ...)
extract_faces_from_frames(frames_dir, out_dir, ...)

Both are idempotent: if the output dir already has the expected number of
crops, they skip work (cheap re-runs on spot-preemption resume).
"""

from __future__ import annotations

import os
import glob
from typing import List, Optional, Tuple


# ---------------------------------------------------------------------------
# Lazy detector construction
# ---------------------------------------------------------------------------
_MTCNN_SINGLETON = None  # cache per-process so we don't rebuild the net per video


def _get_mtcnn(device: str = "cpu", image_size: int = 380, margin_px: int = 0):
    """Build (once) and return an MTCNN detector, or None if unavailable.

    We deliberately set ``keep_all=True`` and pick the largest face ourselves,
    because in deepfake videos the swapped face is usually the largest, most
    central one and MTCNN's default "first" is not guaranteed largest.
    """
    global _MTCNN_SINGLETON
    if _MTCNN_SINGLETON is not None:
        return _MTCNN_SINGLETON
    try:
        from facenet_pytorch import MTCNN  # type: ignore

        _MTCNN_SINGLETON = MTCNN(
            image_size=image_size,
            margin=margin_px,
            keep_all=True,
            post_process=False,   # we want raw crops, not whitened tensors
            select_largest=True,
            device=device,
        )
        return _MTCNN_SINGLETON
    except Exception as exc:  # pragma: no cover - depends on optional dep
        print(f"[face_extract] MTCNN unavailable ({exc}); using Haar fallback.")
        return None


def _haar_detect_largest(bgr_image) -> Optional[Tuple[int, int, int, int]]:
    """OpenCV Haar fallback. Returns the largest face box (x, y, w, h) or None."""
    import cv2  # local import

    gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
    cascade_path = os.path.join(
        cv2.data.haarcascades, "haarcascade_frontalface_default.xml"
    )
    cascade = cv2.CascadeClassifier(cascade_path)
    faces = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5,
                                     minSize=(60, 60))
    if len(faces) == 0:
        return None
    # largest by area
    return max(faces, key=lambda b: b[2] * b[3])


def _crop_with_margin(rgb_image, box, margin: float, out_size: int):
    """Expand ``box`` (x1, y1, x2, y2) by ``margin`` fraction, crop, resize.

    Returns an RGB uint8 numpy array of shape (out_size, out_size, 3).
    """
    import cv2
    import numpy as np

    h, w = rgb_image.shape[:2]
    x1, y1, x2, y2 = box
    bw, bh = x2 - x1, y2 - y1
    mx, my = bw * margin, bh * margin
    x1 = max(0, int(x1 - mx))
    y1 = max(0, int(y1 - my))
    x2 = min(w, int(x2 + mx))
    y2 = min(h, int(y2 + my))
    crop = rgb_image[y1:y2, x1:x2]
    if crop.size == 0:
        return None
    crop = cv2.resize(crop, (out_size, out_size), interpolation=cv2.INTER_AREA)
    return crop.astype(np.uint8)


def _detect_largest_box(rgb_image, mtcnn) -> Optional[Tuple[float, float, float, float]]:
    """Return the largest face box in (x1, y1, x2, y2) using MTCNN or Haar."""
    import numpy as np

    if mtcnn is not None:
        try:
            boxes, probs = mtcnn.detect(rgb_image)
            if boxes is not None and len(boxes) > 0:
                areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in boxes]
                return tuple(boxes[int(np.argmax(areas))])
        except Exception:
            pass  # fall through to Haar
    # Haar fallback expects BGR
    import cv2
    bgr = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
    box = _haar_detect_largest(bgr)
    if box is None:
        return None
    x, y, bw, bh = box
    return (float(x), float(y), float(x + bw), float(y + bh))


def _even_frame_indices(total: int, n: int) -> List[int]:
    """Evenly-spaced sample of ``n`` indices from ``[0, total)``."""
    if total <= 0:
        return []
    if n >= total:
        return list(range(total))
    step = total / float(n)
    return sorted({int(i * step) for i in range(n)})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def extract_faces_from_video(
    video_path: str,
    out_dir: str,
    frames_per_video: int = 16,
    out_size: int = 380,
    margin: float = 0.30,
    device: str = "cpu",
    overwrite: bool = False,
) -> int:
    """Extract aligned face crops from a single video.

    Samples ``frames_per_video`` frames evenly across the clip, detects the
    largest face in each, expands by ``margin`` and writes ``out_size`` crops to
    ``out_dir`` as ``frame_<idx>.png``. Returns the number of crops written.

    Idempotent: if crops already exist and ``overwrite`` is False, returns the
    existing count without re-decoding the video.
    """
    import cv2

    os.makedirs(out_dir, exist_ok=True)
    existing = glob.glob(os.path.join(out_dir, "frame_*.png"))
    if existing and not overwrite:
        return len(existing)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"[face_extract] could not open {video_path}")
        return 0
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
    wanted = set(_even_frame_indices(total, frames_per_video)) if total > 0 else None

    mtcnn = _get_mtcnn(device=device, image_size=out_size)
    written = 0
    no_face = 0
    idx = 0
    saved = 0

    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            break
        take = (wanted is None) or (idx in wanted)
        if take:
            rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            box = _detect_largest_box(rgb, mtcnn)
            if box is not None:
                crop = _crop_with_margin(rgb, box, margin, out_size)
                if crop is not None:
                    out_path = os.path.join(out_dir, f"frame_{saved:04d}.png")
                    cv2.imwrite(out_path, cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
                    written += 1
                    saved += 1
            else:
                no_face += 1
            # If we couldn't get a frame-count (streaming), stop after enough.
            if wanted is None and saved >= frames_per_video:
                break
        idx += 1

    cap.release()
    if written == 0:
        print(f"[face_extract] no faces in {os.path.basename(video_path)} "
              f"(skipped {no_face} frames)")
    return written


def extract_faces_from_frames(
    frames_dir: str,
    out_dir: str,
    out_size: int = 380,
    margin: float = 0.30,
    device: str = "cpu",
    overwrite: bool = False,
    max_frames: Optional[int] = None,
) -> int:
    """Extract aligned face crops from a folder of already-decoded frames.

    Useful for datasets shipped as image folders (e.g. diffusion sets, or the
    repo's ``celeb_df_v2_frames.zip``). Reads ``*.png/*.jpg/*.jpeg`` from
    ``frames_dir``, optionally evenly-subsamples to ``max_frames``, detects the
    largest face and writes crops. Returns the number written. Idempotent.
    """
    import cv2

    os.makedirs(out_dir, exist_ok=True)
    existing = glob.glob(os.path.join(out_dir, "frame_*.png"))
    if existing and not overwrite:
        return len(existing)

    paths: List[str] = []
    for ext in ("*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG"):
        paths.extend(glob.glob(os.path.join(frames_dir, ext)))
    paths.sort()
    if not paths:
        return 0
    if max_frames is not None and len(paths) > max_frames:
        idxs = _even_frame_indices(len(paths), max_frames)
        paths = [paths[i] for i in idxs]

    mtcnn = _get_mtcnn(device=device, image_size=out_size)
    written = 0
    for p in paths:
        bgr = cv2.imread(p)
        if bgr is None:
            continue
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        box = _detect_largest_box(rgb, mtcnn)
        if box is None:
            continue
        crop = _crop_with_margin(rgb, box, margin, out_size)
        if crop is None:
            continue
        out_path = os.path.join(out_dir, f"frame_{written:04d}.png")
        cv2.imwrite(out_path, cv2.cvtColor(crop, cv2.COLOR_RGB2BGR))
        written += 1
    return written


def extract_dataset(
    src_root: str,
    dst_root: str,
    kind: str,
    frames_per_video: int = 16,
    out_size: int = 380,
    margin: float = 0.30,
    device: str = "cpu",
    video_exts: Tuple[str, ...] = (".mp4", ".avi", ".mov", ".mkv"),
) -> dict:
    """Walk a dataset tree and extract crops, preserving real/fake/identity dirs.

    Input layout (videos):   <src_root>/{real,fake}/<identity>/<clip>.mp4
    Input layout (frames):   <src_root>/{real,fake}/<identity>/<clip>/<frame>.png
    Output layout:           <dst_root>/{real,fake}/<identity>/<clip>/frame_*.png

    The identity directory is preserved so dataset.py can build identity-disjoint
    splits. Returns a small stats dict. Idempotent at the clip level.
    """
    stats = {"clips": 0, "crops": 0, "empty_clips": 0}
    for label in ("real", "fake"):
        label_src = os.path.join(src_root, label)
        if not os.path.isdir(label_src):
            continue
        # identity dirs (fall back to a single bucket if flat)
        identities = [d for d in os.listdir(label_src)
                      if os.path.isdir(os.path.join(label_src, d))]
        if not identities:
            identities = ["_flat"]
        for ident in identities:
            ident_src = os.path.join(label_src, ident) if ident != "_flat" else label_src
            if kind == "video":
                clips = [f for f in os.listdir(ident_src)
                         if os.path.splitext(f)[1].lower() in video_exts]
                for clip in clips:
                    clip_name = os.path.splitext(clip)[0]
                    out_dir = os.path.join(dst_root, label, ident, clip_name)
                    n = extract_faces_from_video(
                        os.path.join(ident_src, clip), out_dir,
                        frames_per_video=frames_per_video, out_size=out_size,
                        margin=margin, device=device,
                    )
                    stats["clips"] += 1
                    stats["crops"] += n
                    if n == 0:
                        stats["empty_clips"] += 1
            else:  # frames
                clip_dirs = [d for d in os.listdir(ident_src)
                             if os.path.isdir(os.path.join(ident_src, d))]
                if not clip_dirs:
                    clip_dirs = ["_frames"]
                for clip in clip_dirs:
                    clip_src = os.path.join(ident_src, clip) if clip != "_frames" else ident_src
                    out_dir = os.path.join(dst_root, label, ident, clip)
                    n = extract_faces_from_frames(
                        clip_src, out_dir, out_size=out_size, margin=margin,
                        device=device, max_frames=frames_per_video,
                    )
                    stats["clips"] += 1
                    stats["crops"] += n
                    if n == 0:
                        stats["empty_clips"] += 1
    return stats
