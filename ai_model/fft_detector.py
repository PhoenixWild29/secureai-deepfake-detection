"""
Frequency-domain deepfake detector.

Technique: azimuthally-averaged log-magnitude FFT spectrum per frame,
followed by logistic regression. Based on:
  Durall, R., Keuper, M., Keuper, J. (ICCV 2019).
  "Unmasking DeepFakes with simple Features."

Why it works: real camera sensors have a specific high-frequency noise
signature (sensor noise + demosaicing + JPEG artifacts). Neural deepfake
generators often can't reproduce this — they fall off differently in the
high-frequency tail of the spectrum. This gives a signal that is orthogonal
to spatial-pixel-based detectors like ResNet50 / ConvNeXt.

Usage:
    from ai_model.fft_detector import FFTDeepfakeDetector

    det = FFTDeepfakeDetector()
    det.load("ai_model/trained_models/fft_detector.pkl")
    prob_fake = det.predict_proba(pil_image)
"""
from __future__ import annotations

import json
import pickle
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------
def _azimuthal_average(image_2d: np.ndarray, center: Optional[Tuple[int, int]] = None) -> np.ndarray:
    """
    Average a 2D array over all angles at each radius from the center.
    Returns a 1D array of length ~min(h, w) / 2.
    """
    h, w = image_2d.shape
    if center is None:
        center = (h // 2, w // 2)
    y, x = np.indices((h, w))
    r = np.sqrt((x - center[1]) ** 2 + (y - center[0]) ** 2)
    r_int = r.astype(int)

    # sum values in each radius bin, divide by count → mean
    tbin = np.bincount(r_int.ravel(), image_2d.ravel())
    nr   = np.bincount(r_int.ravel())
    radial_mean = tbin / np.maximum(nr, 1)
    return radial_mean


def extract_fft_spectrum(pil_img: Image.Image, size: int = 224) -> np.ndarray:
    """
    Extract the azimuthally-averaged log-magnitude FFT spectrum of an image.

    Steps:
      1. Convert to grayscale, resize to size x size
      2. 2D FFT, shift zero-frequency to center
      3. Magnitude, log-transform (log1p)
      4. Azimuthal averaging → 1D radial spectrum

    Returns a 1D numpy array of length `size // 2` (e.g., 112 for size=224).
    Consistent-length regardless of input resolution, so can be stacked.
    """
    img = pil_img.convert("L").resize((size, size), Image.BILINEAR)
    arr = np.array(img, dtype=np.float32) / 255.0
    # Hanning window to reduce spectral leakage at image edges
    win = np.outer(np.hanning(size), np.hanning(size))
    arr = arr * win

    f = np.fft.fft2(arr)
    f_shift = np.fft.fftshift(f)
    magnitude = np.log1p(np.abs(f_shift))
    spectrum = _azimuthal_average(magnitude)

    # Trim to exactly size//2 — azimuthal averaging can return size//2 or size//2+1
    N = size // 2
    return spectrum[:N].astype(np.float32)


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------
class FFTDeepfakeDetector:
    """
    Logistic regression classifier on FFT radial spectra.

    Fit phase:  .fit(real_paths, fake_paths)
    Save/load:  .save(path) / .load(path)
    Inference:  .predict_proba(pil_image) -> float in [0, 1] (P(fake))
                .predict_proba_batch(pil_images) -> List[float]
    """

    def __init__(self, size: int = 224):
        self.size = size
        self.classifier = None
        self.scaler = None
        self.metadata = {}

    # ---- training ----
    def fit(self, real_paths: List[Path], fake_paths: List[Path],
            C: float = 1.0, verbose: bool = True) -> dict:
        """
        Fit a logistic regression on (real, fake) image paths.

        Returns a dict with train AUC for sanity check.
        """
        from sklearn.linear_model import LogisticRegression
        from sklearn.preprocessing import StandardScaler
        from sklearn.metrics import roc_auc_score
        import time

        X, y = [], []
        all_paths = [(p, 0) for p in real_paths] + [(p, 1) for p in fake_paths]
        t0 = time.time()
        for i, (p, label) in enumerate(all_paths):
            try:
                img = Image.open(p).convert("RGB")
            except Exception as e:
                if verbose:
                    print(f"  [skip] {p.name}: {e}")
                continue
            X.append(extract_fft_spectrum(img, self.size))
            y.append(label)
            if verbose and (i + 1) % 500 == 0:
                elapsed = time.time() - t0
                eta = elapsed / (i + 1) * (len(all_paths) - (i + 1))
                print(f"    [{i+1}/{len(all_paths)}]  {elapsed:.0f}s elapsed  ETA {eta:.0f}s")

        X = np.stack(X)
        y = np.array(y)
        if verbose:
            print(f"\n  Feature matrix: {X.shape}  (real={int((y==0).sum())}  fake={int((y==1).sum())})")

        # Standardize features (FFT magnitudes have huge range)
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.classifier = LogisticRegression(C=C, max_iter=2000, class_weight="balanced")
        self.classifier.fit(X_scaled, y)

        train_probs = self.classifier.predict_proba(X_scaled)[:, 1]
        train_auc = roc_auc_score(y, train_probs)

        self.metadata = {
            "size": self.size,
            "C": C,
            "feature_dim": X.shape[1],
            "n_real": int((y == 0).sum()),
            "n_fake": int((y == 1).sum()),
            "train_auc": float(train_auc),
        }

        if verbose:
            print(f"\n  [OK] train AUC = {train_auc:.4f}  (n={len(y)}, C={C})")
        return {"train_auc": float(train_auc), "n": len(y), "feature_dim": X.shape[1]}

    # ---- inference ----
    def predict_proba(self, pil_img: Image.Image) -> float:
        if self.classifier is None or self.scaler is None:
            raise RuntimeError("FFT detector not fitted. Call .fit() or .load() first.")
        x = extract_fft_spectrum(pil_img, self.size).reshape(1, -1)
        x = self.scaler.transform(x)
        return float(self.classifier.predict_proba(x)[0, 1])

    def predict_proba_batch(self, pil_imgs: List[Image.Image]) -> List[float]:
        if self.classifier is None or self.scaler is None:
            raise RuntimeError("FFT detector not fitted. Call .fit() or .load() first.")
        X = np.stack([extract_fft_spectrum(img, self.size) for img in pil_imgs])
        X = self.scaler.transform(X)
        return self.classifier.predict_proba(X)[:, 1].tolist()

    # ---- persistence ----
    def save(self, path: str):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "wb") as f:
            pickle.dump({
                "size": self.size,
                "classifier": self.classifier,
                "scaler": self.scaler,
                "metadata": self.metadata,
            }, f)

    def load(self, path: str):
        with open(path, "rb") as f:
            d = pickle.load(f)
        self.size = d["size"]
        self.classifier = d["classifier"]
        self.scaler = d["scaler"]
        self.metadata = d.get("metadata", {})
        return self


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse
    import random

    parser = argparse.ArgumentParser(description="Train / test FFT deepfake detector")
    parser.add_argument("--train-real", default="datasets/celeb_df_v2_frames/train/real")
    parser.add_argument("--train-fake", default="datasets/celeb_df_v2_frames/train/fake")
    parser.add_argument("--val-real", default="datasets/celeb_df_v2_frames/val/real")
    parser.add_argument("--val-fake", default="datasets/celeb_df_v2_frames/val/fake")
    parser.add_argument("--test-real", default="datasets/celeb_df_v2_frames/test/real")
    parser.add_argument("--test-fake", default="datasets/celeb_df_v2_frames/test/fake")
    parser.add_argument("--n-train-per-class", type=int, default=2000)
    parser.add_argument("--n-eval-per-class",  type=int, default=500)
    parser.add_argument("--C", type=float, default=1.0)
    parser.add_argument("--out", default="ai_model/trained_models/fft_detector.pkl")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)

    def sample(dir_path, n):
        files = sorted(Path(dir_path).glob("*.jpg"))
        random.shuffle(files)
        return files[:n]

    tr_real = sample(args.train_real, args.n_train_per_class)
    tr_fake = sample(args.train_fake, args.n_train_per_class)
    va_real = sample(args.val_real,   args.n_eval_per_class)
    va_fake = sample(args.val_fake,   args.n_eval_per_class)
    te_real = sample(args.test_real,  args.n_eval_per_class)
    te_fake = sample(args.test_fake,  args.n_eval_per_class)

    print(f"Training set: {len(tr_real)} real + {len(tr_fake)} fake")
    print(f"Val set:      {len(va_real)} real + {len(va_fake)} fake")
    print(f"Test set:     {len(te_real)} real + {len(te_fake)} fake")

    print("\n--- Training FFT detector ---")
    det = FFTDeepfakeDetector()
    det.fit(tr_real, tr_fake, C=args.C)

    from sklearn.metrics import roc_auc_score, accuracy_score, f1_score
    def evaluate(name, real_paths, fake_paths):
        probs, labels = [], []
        for p in real_paths:
            try:
                probs.append(det.predict_proba(Image.open(p).convert("RGB")))
                labels.append(0)
            except Exception:
                pass
        for p in fake_paths:
            try:
                probs.append(det.predict_proba(Image.open(p).convert("RGB")))
                labels.append(1)
            except Exception:
                pass
        probs = np.array(probs); labels = np.array(labels)
        auc = roc_auc_score(labels, probs)
        acc = accuracy_score(labels, probs > 0.5)
        f1  = f1_score(labels, probs > 0.5)
        print(f"  {name:5s}  AUC: {auc:.4f}  Acc: {acc:.4f}  F1: {f1:.4f}  (n={len(labels)})")
        return {"auc": auc, "accuracy": acc, "f1": f1, "n": int(len(labels))}

    print("\n--- Evaluation ---")
    val_metrics  = evaluate("val",  va_real, va_fake)
    test_metrics = evaluate("test", te_real, te_fake)

    # Save
    det.metadata["val_metrics"]  = val_metrics
    det.metadata["test_metrics"] = test_metrics
    det.save(args.out)
    print(f"\n[OK] Saved FFT detector to {args.out}")
    print(f"     Metadata: {json.dumps(det.metadata, indent=2)}")
