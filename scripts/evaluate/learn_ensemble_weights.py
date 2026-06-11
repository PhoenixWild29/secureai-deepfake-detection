#!/usr/bin/env python3
"""
Learn ensemble weights by fitting logistic regression on validation-set scores.

Pipeline:
  1. Sample N frames from datasets/celeb_df_v2_frames/val/{real,fake}
  2. Run CLIP, LAA-Net, ResNet50 on each frame
  3. Fit logistic regression on (clip, laa, resnet50) -> label (0=real, 1=fake)
  4. Save learned coefficients and intercept to ai_model/trained_models/ensemble_weights.json

The detector's detect() method loads this file at runtime if present.
"""
import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

# Make repo root importable
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from PIL import Image
import numpy as np


def sample_frames(val_root: Path, n_per_class: int, seed: int = 42):
    random.seed(seed)
    real_files = sorted((val_root / "real").glob("*.jpg"))
    fake_files = sorted((val_root / "fake").glob("*.jpg"))
    random.shuffle(real_files)
    random.shuffle(fake_files)
    real_sample = real_files[:n_per_class]
    fake_sample = fake_files[:n_per_class]
    print(f"  Real frames available: {len(real_files):,}  -> using {len(real_sample)}")
    print(f"  Fake frames available: {len(fake_files):,}  -> using {len(fake_sample)}")
    return real_sample, fake_sample


def collect_scores(detector, frame_paths, label):
    """Run all available detectors on each frame; return list of dicts."""
    rows = []
    t0 = time.time()
    has_convnext = getattr(detector, "convnext_available", False)
    has_fft      = getattr(detector, "fft_available", False)
    for i, p in enumerate(frame_paths):
        try:
            img = Image.open(p).convert("RGB")
        except Exception as e:
            print(f"  [skip] {p.name}: {e}")
            continue

        clip_probs   = detector.clip_detect_frames_probs([img])
        laa_probs    = detector.laa_detect_frames_probs([img]) if detector.laa_available else [0.5]
        resnet_probs = detector.resnet50_detect_frames_probs([img]) if detector.resnet50_available else [0.5]

        row = {
            "path":     str(p.name),
            "label":    label,
            "clip":     float(clip_probs[0]),
            "laa":      float(laa_probs[0]),
            "resnet50": float(resnet_probs[0]),
        }
        if has_convnext:
            row["convnext"] = float(detector.convnext_detect_frames_probs([img])[0])
        if has_fft:
            row["fft"] = float(detector.fft_detect_frames_probs([img])[0])
        rows.append(row)

        if (i + 1) % 20 == 0:
            elapsed = time.time() - t0
            rate = (i + 1) / elapsed
            eta = (len(frame_paths) - (i + 1)) / max(rate, 1e-9)
            print(f"    [{i+1}/{len(frame_paths)}] {elapsed:.0f}s elapsed, ETA {eta:.0f}s")
    return rows


def fit_weights(rows, out_path, C=1.0):
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    # Detect which detectors are present in the rows
    detector_names = [d for d in ("clip", "laa", "resnet50", "convnext", "fft") if d in rows[0]]
    print(f"  Detectors in data: {detector_names}")

    X = np.array([[r[d] for d in detector_names] for r in rows])
    y = np.array([r["label"] for r in rows])

    # Baseline: individual AUCs on this val sample
    print("\n  Val-sample AUCs (per detector):")
    individual_aucs = {}
    for i, name in enumerate(detector_names):
        try:
            auc = roc_auc_score(y, X[:, i])
            individual_aucs[name] = float(auc)
            print(f"    {name:10s}: {auc:.4f}")
        except ValueError:
            individual_aucs[name] = None
            print(f"    {name:10s}: n/a (single class)")

    # Unweighted mean baseline
    unweighted = X.mean(axis=1)
    unweighted_auc = roc_auc_score(y, unweighted)
    print(f"    unweighted mean: {unweighted_auc:.4f}")

    # Fit logistic regression
    clf = LogisticRegression(C=C, max_iter=1000)
    clf.fit(X, y)
    print(f"  (logistic regression C={C})")

    coefs = clf.coef_[0].tolist()
    intercept = float(clf.intercept_[0])

    logits = X @ np.array(coefs) + intercept
    learned_auc = roc_auc_score(y, logits)
    print(f"    learned weights (train AUC): {learned_auc:.4f}")

    weights = {
        "detectors": detector_names,
        "coefficients": coefs,
        "intercept": intercept,
        "val_sample_size": len(rows),
        "val_auc_individual": {
            **{k: v for k, v in individual_aucs.items()},
            "unweighted_mean": float(unweighted_auc),
            "learned":         float(learned_auc),
        },
        "C": C,
        "note": "Apply as sigmoid(intercept + sum(coef_i * prob_i)) to get ensemble fake probability.",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(weights, f, indent=2)

    print(f"\n  Coefficients:")
    for name, c in zip(detector_names, coefs):
        print(f"    {name:10s}: {c:+.4f}")
    print(f"    intercept : {intercept:+.4f}")
    print(f"\n  Saved to: {out_path}")
    return weights


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--val-root", default="datasets/celeb_df_v2_frames/val")
    parser.add_argument("--n-per-class", type=int, default=200,
                        help="Frames sampled from each class (default 200)")
    parser.add_argument("--scores-out", default="ai_model/trained_models/val_scores.json")
    parser.add_argument("--weights-out", default="ai_model/trained_models/ensemble_weights.json")
    parser.add_argument("--skip-collect", action="store_true",
                        help="Skip score collection, re-fit using existing val_scores.json")
    parser.add_argument("--C", type=float, default=1.0,
                        help="Inverse L2 regularization strength (smaller = more regularization)")
    args = parser.parse_args()

    val_root = Path(args.val_root)
    scores_out = Path(args.scores_out)
    weights_out = Path(args.weights_out)

    if args.skip_collect and scores_out.exists():
        print(f"Loading cached scores from {scores_out}")
        with open(scores_out) as f:
            rows = json.load(f)
    else:
        print("Loading EnhancedDetector ...")
        from ai_model.enhanced_detector import EnhancedDetector
        detector = EnhancedDetector()
        print(f"  laa_available:     {detector.laa_available}")
        print(f"  resnet50_available: {detector.resnet50_available}\n")

        real_sample, fake_sample = sample_frames(val_root, args.n_per_class)

        print(f"\nScoring {len(real_sample)} real frames ...")
        real_rows = collect_scores(detector, real_sample, label=0)
        print(f"\nScoring {len(fake_sample)} fake frames ...")
        fake_rows = collect_scores(detector, fake_sample, label=1)

        rows = real_rows + fake_rows
        scores_out.parent.mkdir(parents=True, exist_ok=True)
        with open(scores_out, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"\n[OK] Saved {len(rows)} rows -> {scores_out}")

    print("\nFitting ensemble weights ...")
    fit_weights(rows, weights_out, C=args.C)


if __name__ == "__main__":
    main()
