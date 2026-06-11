"""Self-Blended Images (SBI) augmentation.

SBI (Shiohara & Yamasaki, "Detecting Deepfakes with Self-Blended Images",
CVPR 2022) is one of the strongest *generalization* recipes in deepfake
detection. The key insight: real face-swap deepfakes all share a common,
manipulation-agnostic artifact — a subtle *blending boundary* where the
generated face is composited onto the background. Instead of training on the
specific fakes of one dataset (which overfits to that generator), SBI
synthesizes pseudo-fakes from REAL images alone by blending a mildly
transformed copy of a face back onto itself. The model then learns the generic
blending artifact and transfers to UNSEEN manipulations — exactly the
cross-dataset goal in MODEL_IMPROVEMENT_PLAN.md (P1.1).

The repo's previous SBI run scored 0.61. That is a misconfiguration, not a
verdict on the method. The two classic ways to break SBI are:
  (1) blending that is too aggressive/visible (the net learns a trivial cue),
      or too weak (no learnable boundary), and
  (2) applying it to non-aligned full frames. Here we apply SBI to *aligned
      face crops* and keep the source/target transforms SUBTLE so the only
      reliable cue is the blending boundary itself.

Pipeline for one real aligned face I:
  1. source  = subtle photometric/geometric jitter of I (color, blur, resize,
               slight translate) — this is the "fake foreground".
  2. target  = I (or a second mild jitter) — the "real background".
  3. mask    = soft facial-region mask (convex hull from landmarks if given,
               else an elliptical face mask), feathered with a Gaussian blur so
               the composite has a smooth, subtle seam.
  4. blended = source * mask + target * (1 - mask)  -> label = 1 (fake)

We return (blended_uint8, mask_float, label).

Heavy imports (numpy, cv2) are local so the module imports without them.
"""

from __future__ import annotations

import random
from typing import Optional, Tuple, List


# ---------------------------------------------------------------------------
# Mask construction
# ---------------------------------------------------------------------------
def _elliptical_face_mask(h: int, w: int):
    """Default face mask: a centered ellipse covering the central face region.

    Used when no landmarks are available. Covers ~the inner 70% so the seam
    falls across cheeks/jaw where real blending artifacts appear.
    """
    import numpy as np
    import cv2

    mask = np.zeros((h, w), dtype=np.float32)
    center = (w // 2, int(h * 0.52))
    axes = (int(w * 0.36), int(h * 0.46))
    cv2.ellipse(mask, center, axes, 0, 0, 360, 1.0, thickness=-1)
    return mask


def _convex_hull_mask(h: int, w: int, landmarks):
    """Build a convex-hull face mask from landmark points (Nx2 array)."""
    import numpy as np
    import cv2

    mask = np.zeros((h, w), dtype=np.float32)
    pts = np.asarray(landmarks, dtype=np.int32).reshape(-1, 2)
    if len(pts) < 3:
        return _elliptical_face_mask(h, w)
    hull = cv2.convexHull(pts)
    cv2.fillConvexPoly(mask, hull, 1.0)
    return mask


def _feather(mask, max_blur: int = 31):
    """Feather a binary-ish mask into a soft alpha so the seam is subtle."""
    import numpy as np
    import cv2

    h, w = mask.shape[:2]
    # blur kernel scaled to face size, forced odd
    k = max(3, int(min(h, w) * 0.06))
    if k % 2 == 0:
        k += 1
    k = min(k, max_blur)
    soft = cv2.GaussianBlur(mask.astype(np.float32), (k, k), 0)
    # random partial alpha so the blend strength varies (prevents trivial cue)
    soft = soft * random.uniform(0.55, 1.0)
    return np.clip(soft, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Source transforms (kept SUBTLE on purpose)
# ---------------------------------------------------------------------------
def _subtle_source_transform(img):
    """Apply mild photometric + geometric jitter to create the swap foreground.

    These are intentionally gentle: large changes would give the classifier a
    color/blur shortcut instead of forcing it to find the blending boundary.
    """
    import numpy as np
    import cv2

    out = img.astype(np.float32)

    # color / brightness jitter (small)
    if random.random() < 0.7:
        out *= random.uniform(0.92, 1.08)                       # brightness
    if random.random() < 0.7:
        mean = out.mean(axis=(0, 1), keepdims=True)
        out = (out - mean) * random.uniform(0.92, 1.08) + mean  # contrast
    if random.random() < 0.5:
        # mild per-channel color shift (hue-ish)
        out += np.array([random.uniform(-6, 6) for _ in range(3)],
                        dtype=np.float32)

    out = np.clip(out, 0, 255).astype(np.uint8)

    # slight blur OR slight sharpen -> resolution mismatch at the seam
    if random.random() < 0.5:
        out = cv2.GaussianBlur(out, (3, 3), 0)
    if random.random() < 0.4:
        # downscale-upscale to mimic a lower-res generated face
        h, w = out.shape[:2]
        s = random.uniform(0.7, 0.95)
        small = cv2.resize(out, (max(1, int(w * s)), max(1, int(h * s))),
                           interpolation=cv2.INTER_AREA)
        out = cv2.resize(small, (w, h), interpolation=cv2.INTER_LINEAR)
    return out


def _small_affine(img, mask):
    """Tiny translation/scale of the foreground+mask to create geometric seam."""
    import numpy as np
    import cv2

    h, w = img.shape[:2]
    tx = random.uniform(-0.03, 0.03) * w
    ty = random.uniform(-0.03, 0.03) * h
    sc = random.uniform(0.97, 1.03)
    M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, sc)
    M[0, 2] += tx
    M[1, 2] += ty
    img2 = cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)
    mask2 = cv2.warpAffine(mask, M, (w, h), borderMode=cv2.BORDER_CONSTANT,
                           borderValue=0.0)
    return img2, mask2


# ---------------------------------------------------------------------------
# Core SBI
# ---------------------------------------------------------------------------
def self_blend(
    image,
    landmarks: Optional[List] = None,
) -> Tuple["object", "object", int]:
    """Generate a self-blended pseudo-fake from a real aligned face.

    Parameters
    ----------
    image : HxWx3 uint8 RGB numpy array (an aligned face crop).
    landmarks : optional list/array of (x, y) facial landmarks for a tighter
        convex-hull mask. If None, an elliptical mask is used.

    Returns
    -------
    (blended_uint8_rgb, mask_float, label) where label == 1 (fake).
    """
    import numpy as np

    img = np.asarray(image)
    if img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
    h, w = img.shape[:2]

    # foreground (the "swapped" face) = subtly transformed copy
    source = _subtle_source_transform(img)
    # background = original (optionally a second very mild jitter)
    target = img if random.random() < 0.5 else _subtle_source_transform(img)

    # facial-region mask
    if landmarks is not None:
        mask = _convex_hull_mask(h, w, landmarks)
    else:
        mask = _elliptical_face_mask(h, w)

    # tiny geometric offset of foreground+mask -> realistic boundary
    source, mask = _small_affine(source, mask)

    # feather mask so the seam is a *subtle* gradient (the learnable artifact)
    alpha = _feather(mask)[..., None]  # HxWx1

    blended = source.astype(np.float32) * alpha + target.astype(np.float32) * (1.0 - alpha)
    blended = np.clip(blended, 0, 255).astype(np.uint8)
    return blended, alpha[..., 0], 1


# ---------------------------------------------------------------------------
# Torch-compatible transform wrapper
# ---------------------------------------------------------------------------
class SBITransform:
    """Callable that, with probability ``prob``, converts a REAL face into an
    SBI pseudo-fake. Intended to be applied inside the Dataset for real images
    *before* the albumentations/normalisation pipeline.

    Usage in a Dataset.__getitem__ for a real sample::

        if self.sbi is not None:
            img, label = self.sbi(img, label, landmarks=lm)

    When it fires, it returns (blended_image, 1). Otherwise (image, original
    label). This keeps the real/fake balance dynamic but still labels SBI
    outputs as fakes (label 1), which is the whole point.
    """

    def __init__(self, prob: float = 0.5):
        self.prob = prob

    def __call__(self, image, label: int, landmarks: Optional[List] = None):
        # Only synthesize fakes from REAL images (label 0).
        if label == 0 and random.random() < self.prob:
            blended, _mask, fake_label = self_blend(image, landmarks=landmarks)
            return blended, fake_label
        return image, label
