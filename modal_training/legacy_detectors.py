"""Run the repo's *legacy* per-image detectors over a set of face crops.

Why this module exists
----------------------
The cross-dataset eval (``evaluate.cross_dataset_report``) already produces the
NEW backbone's per-sample fake-probability. To do a genuine ensemble *refit*
(``ensemble_refit.py``) we also need, for the SAME samples, the per-image score
from every legacy detector the learned ensemble combines:

    ["clip", "laa", "resnet50", "convnext", "fft"]

Previously those columns were neutral-filled with 0.5, which makes the refit a
no-op for them. This module recomputes the REAL columns by reusing the existing
detector code in ``ai_model/enhanced_detector.py`` — it does **not** reimplement
any model. ``EnhancedDetector`` already wraps all five detectors and exposes a
per-frame scorer for each that takes ``List[PIL.Image]`` and returns a list of
fake probabilities in ``[0, 1]``:

    clip      -> EnhancedDetector.clip_detect_frames_probs
    laa       -> EnhancedDetector.laa_detect_frames_probs
    resnet50  -> EnhancedDetector.resnet50_detect_frames_probs
    convnext  -> EnhancedDetector.convnext_detect_frames_probs
    fft       -> EnhancedDetector.fft_detect_frames_probs

The input images are ALREADY aligned face crops (written by
``face_extract.extract_dataset``), so we construct the detector with
``use_face_crop=False`` to avoid a redundant second face-crop pass.

Design goals
------------
* Lazy + heavy imports live inside the functions so importing this module
  needs only the standard library + numpy.
* Each detector is loaded ONCE (the single ``EnhancedDetector`` instance loads
  them all) and run in batches over the crops.
* Graceful degradation: if a weight file / dependency is missing, that detector
  is simply OMITTED from the returned dict (a warning is logged) rather than
  crashing the whole evaluation. A totally failed load returns ``{}`` so the
  caller can fall back to neutral-fill behaviour.
* CPU-safe: everything runs under ``torch.no_grad`` inside the detector methods,
  and no CUDA is required.

Public API
----------
``compute_detector_scores(image_paths, device=None, batch_size=64) -> Dict[str, np.ndarray]``
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# Canonical legacy detector order (matches ai_model/trained_models/ensemble_weights.json).
LEGACY_DETECTORS: List[str] = ["clip", "laa", "resnet50", "convnext", "fft"]


# ---------------------------------------------------------------------------
# Import-path robustness
# ---------------------------------------------------------------------------
def _ensure_repo_on_path() -> None:
    """Add the repo root (parent of ``modal_training/``) to ``sys.path``.

    ``ai_model`` is a top-level package in the repo root. When this code runs as
    ``modal_training.legacy_detectors`` the repo root is usually already on the
    path, but on Modal / ad-hoc invocations it may not be — so we add it
    defensively and idempotently.
    """
    here = os.path.dirname(os.path.abspath(__file__))   # .../modal_training
    repo_root = os.path.dirname(here)                   # repo root
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)


# ---------------------------------------------------------------------------
# Image loading
# ---------------------------------------------------------------------------
def _load_images(paths: Sequence[str]) -> List[object]:
    """Load each crop path as an RGB ``PIL.Image``.

    Unreadable paths are replaced with a neutral grey 224x224 image so the
    per-detector arrays stay aligned 1:1 with ``image_paths`` (a missing file
    must not shift every subsequent sample's score). A warning is logged once
    per failure.
    """
    from PIL import Image  # heavy-ish; keep local

    images: List[Image.Image] = []
    for p in paths:
        try:
            with Image.open(p) as im:
                images.append(im.convert("RGB").copy())
        except Exception as exc:  # corrupt / missing file
            logger.warning("[legacy_detectors] could not read %s (%s); "
                           "using neutral grey placeholder.", p, exc)
            images.append(Image.new("RGB", (224, 224), (128, 128, 128)))
    return images


# ---------------------------------------------------------------------------
# Detector construction
# ---------------------------------------------------------------------------
def _build_enhanced_detector(device: Optional[str]):
    """Construct the repo's ``EnhancedDetector`` (loads all 5 detectors once).

    Returns ``None`` if the detector cannot be constructed at all (e.g. CLIP /
    open_clip unavailable) — the caller then degrades to neutral-fill. We pass
    ``use_face_crop=False`` because the inputs are already aligned face crops.
    """
    _ensure_repo_on_path()
    try:
        from ai_model.enhanced_detector import EnhancedDetector
    except Exception as exc:
        logger.warning("[legacy_detectors] cannot import EnhancedDetector (%s); "
                       "skipping legacy detector scores entirely.", exc)
        return None

    try:
        # use_face_crop=False: crops are already aligned faces, so a second crop
        # pass would be wasteful and could distort the input the legacy models
        # were calibrated on.
        detector = EnhancedDetector(device=device, use_face_crop=False)
        return detector
    except Exception as exc:
        logger.warning("[legacy_detectors] EnhancedDetector init failed (%s); "
                       "skipping legacy detector scores entirely.", exc)
        return None


# Map detector key -> (attribute flagging availability, bound-method name).
# ``clip`` has no availability flag because CLIP is always loaded if the
# detector constructed at all.
_DETECTOR_METHODS = {
    "clip":     (None,                 "clip_detect_frames_probs"),
    "laa":      ("laa_available",      "laa_detect_frames_probs"),
    "resnet50": ("resnet50_available", "resnet50_detect_frames_probs"),
    "convnext": ("convnext_available", "convnext_detect_frames_probs"),
    "fft":      ("fft_available",      "fft_detect_frames_probs"),
}


def _run_detector(detector, key: str, images: List[object],
                  batch_size: int) -> Optional["object"]:
    """Run one legacy detector over all images; return a float32 np array.

    Returns ``None`` if the detector is unavailable or every batch failed, so
    the caller can OMIT the column (rather than emit a misleading 0.5 column).
    The per-frame methods accept a ``List[PIL.Image]`` and return one fake
    probability per image, so we simply chunk the images for memory friendliness
    and concatenate.
    """
    import numpy as np

    flag_attr, method_name = _DETECTOR_METHODS[key]

    # Availability gate (CLIP has no flag and is assumed present).
    if flag_attr is not None and not getattr(detector, flag_attr, False):
        logger.info("[legacy_detectors] '%s' not available on detector; "
                    "omitting its column.", key)
        return None

    method = getattr(detector, method_name, None)
    if method is None:
        logger.warning("[legacy_detectors] detector has no method '%s'; "
                       "omitting '%s'.", method_name, key)
        return None

    scores: List[float] = []
    try:
        for start in range(0, len(images), batch_size):
            chunk = images[start:start + batch_size]
            probs = method(chunk)  # List[float], one per image
            # Defensive: methods may return [0.5] when a chunk wholly fails.
            if len(probs) != len(chunk):
                if len(probs) == 1:
                    probs = list(probs) * len(chunk)
                elif len(probs) < len(chunk):
                    probs = list(probs) + [0.5] * (len(chunk) - len(probs))
                else:
                    probs = list(probs)[:len(chunk)]
            scores.extend(float(p) for p in probs)
    except Exception as exc:
        logger.warning("[legacy_detectors] '%s' failed during inference (%s); "
                       "omitting its column.", key, exc)
        return None

    if len(scores) != len(images):
        logger.warning("[legacy_detectors] '%s' produced %d scores for %d "
                       "images; omitting its column.", key, len(scores), len(images))
        return None

    arr = np.asarray(scores, dtype="float32")
    # A column that is entirely the neutral 0.5 placeholder carries no signal
    # (the detector silently failed per-frame); treat it as unavailable so the
    # refit doesn't waste a coefficient on a constant column.
    if arr.size and np.allclose(arr, 0.5):
        logger.info("[legacy_detectors] '%s' returned an all-0.5 (neutral) "
                    "column; omitting it.", key)
        return None
    return arr


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def compute_detector_scores(
    image_paths: Sequence[str],
    device: Optional[str] = None,
    batch_size: int = 64,
    detectors: Optional[Sequence[str]] = None,
) -> Dict[str, "object"]:
    """Score ``image_paths`` (aligned face crops) with each legacy detector.

    Parameters
    ----------
    image_paths:
        Paths to aligned face-crop images, in the SAME order as the eval
        labels/probs they accompany. The returned arrays are aligned 1:1.
    device:
        ``"cpu"`` / ``"cuda"`` / ``None`` (auto). Forwarded to the detector.
    batch_size:
        How many crops to feed each per-frame call at once (memory friendliness).
    detectors:
        Optional subset of ``LEGACY_DETECTORS`` to run. Defaults to all five.

    Returns
    -------
    ``dict[str, np.ndarray]`` mapping detector_key -> float32 array of fake
    probabilities (length == ``len(image_paths)``). Detectors whose weights /
    dependencies are missing, or that fail, are OMITTED from the dict (with a
    logged warning) rather than crashing the eval. If the detector stack cannot
    be constructed at all, an EMPTY dict is returned — the caller then falls
    back to neutral-filling those columns in ``ensemble_refit``.
    """
    out: Dict[str, object] = {}
    if not image_paths:
        return out

    wanted = list(detectors) if detectors else list(LEGACY_DETECTORS)

    detector = _build_enhanced_detector(device)
    if detector is None:
        return out

    # Load all crops once (shared across detectors).
    images = _load_images(image_paths)

    for key in wanted:
        if key not in _DETECTOR_METHODS:
            logger.warning("[legacy_detectors] unknown detector key '%s'; "
                           "skipping.", key)
            continue
        arr = _run_detector(detector, key, images, batch_size)
        if arr is not None:
            out[key] = arr
            logger.info("[legacy_detectors] computed '%s' over %d crops "
                        "(mean=%.4f).", key, len(arr), float(arr.mean()))

    if not out:
        logger.warning("[legacy_detectors] no legacy detector produced scores; "
                       "ensemble refit will neutral-fill all legacy columns.")
    return out
