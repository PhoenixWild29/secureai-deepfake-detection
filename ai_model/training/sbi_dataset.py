"""
Self-Blended Images (SBI) dataset.

Based on:
  Shiohara & Yamasaki, "Detecting Deepfakes with Self-Blended Images",
  CVPR 2022. https://arxiv.org/abs/2204.08376

Key idea: generate synthetic "fake" training samples by self-blending a real
face image back onto a perturbed copy of itself. The model learns to detect
the subtle blending artifacts that appear wherever any fake manipulation has
occurred. This generalizes to unseen deepfake methods because all face-swap /
reenactment / diffusion techniques leave blending traces.

This implementation is simplified for pre-cropped face frames (224x224):
  - Uses an elliptical mask centered on the image (no landmark detection needed)
  - Alpha-blends perturbed source onto target
  - Perturbations: color jitter, small geometric transforms, blur

Usage:
    from ai_model.training.sbi_dataset import SBIDataset
    ds = SBIDataset("datasets/celeb_df_v2_frames/train/real", transform=train_tf)
    loader = DataLoader(ds, batch_size=64, shuffle=True)
"""
from __future__ import annotations

import random
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np
from PIL import Image, ImageFilter
from torch.utils.data import Dataset


# ---------------------------------------------------------------------------
# Core SBI operation
# ---------------------------------------------------------------------------
def _random_color_jitter(img: np.ndarray, rng: random.Random) -> np.ndarray:
    """Small color perturbation: brightness, contrast, saturation, hue."""
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV).astype(np.int32)
    hsv[..., 0] = (hsv[..., 0] + rng.randint(-8, 8)) % 180        # hue shift
    hsv[..., 1] = np.clip(hsv[..., 1] * rng.uniform(0.85, 1.15), 0, 255)  # saturation
    hsv[..., 2] = np.clip(hsv[..., 2] * rng.uniform(0.85, 1.15), 0, 255)  # brightness
    return cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)


def _random_geometric(img: np.ndarray, rng: random.Random) -> np.ndarray:
    """Small scale/rotate/translate to create blending-boundary artifacts."""
    h, w = img.shape[:2]
    angle = rng.uniform(-4, 4)
    scale = rng.uniform(0.97, 1.03)
    tx = rng.uniform(-0.02, 0.02) * w
    ty = rng.uniform(-0.02, 0.02) * h
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle, scale)
    M[0, 2] += tx
    M[1, 2] += ty
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT_101)


def _maybe_blur(img: np.ndarray, rng: random.Random) -> np.ndarray:
    """Occasional light blur to simulate rendering softness."""
    if rng.random() < 0.3:
        k = rng.choice([3, 5])
        img = cv2.GaussianBlur(img, (k, k), 0)
    return img


def _build_elliptical_mask(h: int, w: int, rng: random.Random) -> np.ndarray:
    """Soft elliptical mask centered on the image, slightly jittered per sample."""
    mask = np.zeros((h, w), dtype=np.float32)
    cx = w // 2 + rng.randint(-4, 4)
    cy = h // 2 + rng.randint(-4, 4)
    # Axes sized to cover face region (pre-cropped frames are mostly face)
    ax = int(w * rng.uniform(0.35, 0.45))
    ay = int(h * rng.uniform(0.40, 0.50))
    angle = rng.uniform(-15, 15)
    cv2.ellipse(mask, (cx, cy), (ax, ay), angle, 0, 360, 1.0, -1)
    # Soft edges: blur the mask so blending is gradient-like (no hard seam)
    mask = cv2.GaussianBlur(mask, (0, 0), sigmaX=rng.uniform(6, 12))
    return np.clip(mask, 0, 1)


def self_blend(img_rgb: np.ndarray, rng: Optional[random.Random] = None) -> np.ndarray:
    """
    Generate a self-blended fake from a real face image.

    Args:
        img_rgb: HxWx3 uint8 RGB array
        rng:     optional seeded RNG

    Returns:
        HxWx3 uint8 RGB array (the SBI fake)
    """
    if rng is None:
        rng = random
    target = img_rgb.copy()
    source = img_rgb.copy()

    # Perturb the source: it's the thing that gets blended back on
    source = _random_color_jitter(source, rng)
    source = _random_geometric(source, rng)
    source = _maybe_blur(source, rng)

    # Also lightly perturb target (not too much — the reference stays nearly real)
    if rng.random() < 0.5:
        target = _random_color_jitter(target, rng)

    # Build soft face mask
    h, w = img_rgb.shape[:2]
    mask = _build_elliptical_mask(h, w, rng)
    mask3 = mask[..., None]

    # Alpha-blend source into target along the mask
    blended = source.astype(np.float32) * mask3 + target.astype(np.float32) * (1 - mask3)
    return np.clip(blended, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------
class SBIDataset(Dataset):
    """
    Emits a mix of real frames (label=0) and SBI-fakes (label=1).

    Each __getitem__ with probability `sbi_prob` generates an SBI fake from the
    chosen real image; otherwise returns the real image unchanged. Standard
    post-transforms (flip, jitter, tensor, normalize) run on either output.

    Args:
        root:      directory containing *.jpg real face frames
        transform: torchvision transform applied to PIL Images (should end with ToTensor+Normalize)
        sbi_prob:  fraction of samples generated as SBI fakes (default 0.5)
        seed:      RNG seed for reproducibility of SBI generation
    """

    def __init__(
        self,
        root: str,
        transform=None,
        sbi_prob: float = 0.5,
        seed: Optional[int] = None,
        extensions: tuple = (".jpg", ".jpeg", ".png"),
    ):
        self.root = Path(root)
        self.transform = transform
        self.sbi_prob = sbi_prob
        self.files: List[Path] = sorted(
            f for f in self.root.rglob("*") if f.suffix.lower() in extensions
        )
        if not self.files:
            raise FileNotFoundError(f"No images found under {root}")
        self._seed = seed

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, idx: int):
        # Per-sample RNG so workers are deterministic given a seed
        if self._seed is not None:
            rng = random.Random(self._seed + idx)
        else:
            rng = random.Random()

        path = self.files[idx]
        img = np.array(Image.open(path).convert("RGB"))

        if rng.random() < self.sbi_prob:
            img = self_blend(img, rng=rng)
            label = 1
        else:
            label = 0

        pil = Image.fromarray(img)
        if self.transform is not None:
            pil = self.transform(pil)
        return pil, label


# ---------------------------------------------------------------------------
# Debugging / visualization helper
# ---------------------------------------------------------------------------
def save_sbi_examples(real_dir: str, out_dir: str, n: int = 8, seed: int = 42):
    """
    Save n side-by-side (real, sbi) comparison images for visual inspection.
    Useful to verify the SBI pipeline produces plausible-looking fakes.
    """
    rng = random.Random(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = sorted(Path(real_dir).glob("*.jpg"))
    rng.shuffle(files)
    files = files[:n]
    for i, f in enumerate(files):
        real = np.array(Image.open(f).convert("RGB"))
        fake = self_blend(real, rng=random.Random(seed + i))
        side_by_side = np.concatenate([real, fake], axis=1)
        Image.fromarray(side_by_side).save(out / f"sbi_example_{i:02d}.jpg", quality=90)
    print(f"Saved {len(files)} comparison examples to {out}")


if __name__ == "__main__":
    # Quick visual test
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--real-dir", default="datasets/celeb_df_v2_frames/train/real")
    parser.add_argument("--out-dir", default="ai_model/training/sbi_examples")
    parser.add_argument("--n", type=int, default=8)
    args = parser.parse_args()
    save_sbi_examples(args.real_dir, args.out_dir, n=args.n)
