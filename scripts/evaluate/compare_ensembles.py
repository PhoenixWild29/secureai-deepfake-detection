#!/usr/bin/env python3
"""
Compare unweighted-mean vs learned-weights ensemble on the Celeb-DF v2 test set.

Samples N frames per class from datasets/celeb_df_v2_frames/test/{real,fake},
runs all 3 detectors, computes AUC for each fusion method.
"""
import argparse
import json
import random
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np
from PIL import Image
from sklearn.metrics import roc_auc_score, f1_score, accuracy_score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-root", default="datasets/celeb_df_v2_frames/test")
    parser.add_argument("--n-per-class", type=int, default=300)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--out", default="ai_model/trained_models/test_comparison.json")
    parser.add_argument("--scores-cache", default="ai_model/trained_models/test_scores.json")
    parser.add_argument("--use-cache", action="store_true", help="Reuse cached test scores")
    parser.add_argument("--C-sweep", action="store_true",
                        help="Refit logistic regression at multiple C values and evaluate each on test")
    args = parser.parse_args()

    random.seed(args.seed)
    test_root = Path(args.test_root)
    real = sorted((test_root / "real").glob("*.jpg"))
    fake = sorted((test_root / "fake").glob("*.jpg"))
    random.shuffle(real); random.shuffle(fake)
    real = real[:args.n_per_class]; fake = fake[:args.n_per_class]
    print(f"Test sample: {len(real)} real + {len(fake)} fake = {len(real)+len(fake)} frames")

    cache = Path(args.scores_cache)
    if args.use_cache and cache.exists():
        print(f"Loading cached test scores from {cache}")
        with open(cache) as f:
            rows = json.load(f)
    else:
        print("Loading detector ...")
        from ai_model.enhanced_detector import EnhancedDetector
        det = EnhancedDetector()
        has_convnext = getattr(det, "convnext_available", False)
        has_fft      = getattr(det, "fft_available", False)
        print(f"  convnext_available: {has_convnext}   fft_available: {has_fft}")
        rows = []
        t0 = time.time()
        all_frames = [(p, 0) for p in real] + [(p, 1) for p in fake]
        for i, (p, label) in enumerate(all_frames):
            try:
                img = Image.open(p).convert("RGB")
            except Exception:
                continue
            c  = det.clip_detect_frames_probs([img])[0]
            l  = det.laa_detect_frames_probs([img])[0]      if det.laa_available      else 0.5
            r  = det.resnet50_detect_frames_probs([img])[0] if det.resnet50_available else 0.5
            row = {"label": label, "clip": float(c), "laa": float(l), "resnet50": float(r)}
            if has_convnext:
                row["convnext"] = float(det.convnext_detect_frames_probs([img])[0])
            if has_fft:
                row["fft"] = float(det.fft_detect_frames_probs([img])[0])
            rows.append(row)
            if (i + 1) % 50 == 0:
                elapsed = time.time() - t0
                eta = elapsed / (i + 1) * (len(all_frames) - (i + 1))
                print(f"  [{i+1}/{len(all_frames)}]  {elapsed:.0f}s elapsed  ETA {eta:.0f}s")
        cache.parent.mkdir(parents=True, exist_ok=True)
        with open(cache, "w") as f:
            json.dump(rows, f, indent=2)
        print(f"  Cached test scores -> {cache}")

    # Detect which detectors are in the test rows (handles both 3- and 4-detector setups)
    detector_names = [d for d in ("clip", "laa", "resnet50", "convnext", "fft") if d in rows[0]]
    print(f"  Detectors in rows: {detector_names}")

    # Load weights file
    with open("ai_model/trained_models/ensemble_weights.json") as f:
        ew = json.load(f)
    weights_detectors = ew["detectors"]
    coefs = ew["coefficients"]
    intercept = ew["intercept"]

    # Stack arrays in the order used by the weights file (may differ from rows)
    y = np.array([r["label"] for r in rows])
    arrays = {d: np.array([r[d] for r in rows]) for d in detector_names}

    # --- Fusion methods ---
    all_detector_arr = np.stack([arrays[d] for d in detector_names], axis=1)
    unweighted = all_detector_arr.mean(axis=1)

    # Compute weighted ensemble — requires all detectors listed in the weights file
    if all(d in arrays for d in weights_detectors):
        logit = intercept + sum(coefs[i] * arrays[d] for i, d in enumerate(weights_detectors))
        weighted = 1.0 / (1.0 + np.exp(-logit))
    else:
        weighted = unweighted  # weights file references missing detectors
        print(f"  [warn] weights file needs {weights_detectors}; missing some. Using unweighted for 'Learned weights'.")

    def metrics(name, probs):
        auc = roc_auc_score(y, probs)
        preds = (probs > 0.5).astype(int)
        acc = accuracy_score(y, preds)
        f1 = f1_score(y, preds)
        print(f"  {name:20s}  AUC: {auc:.4f}  Acc: {acc:.4f}  F1: {f1:.4f}")
        return {"auc": auc, "accuracy": acc, "f1": f1}

    print(f"\n{'='*60}")
    print(f"TEST-SET COMPARISON ({len(y)} frames)")
    print(f"{'='*60}")
    results = {}
    for d in detector_names:
        results[f"{d}_only"] = metrics(f"{d.capitalize()} only", arrays[d])
    results["unweighted_mean"] = metrics("Unweighted mean", unweighted)
    results["learned_weights"] = metrics("Learned weights", weighted)

    gain = results["learned_weights"]["auc"] - results["unweighted_mean"]["auc"]
    print(f"\n  Learned vs Unweighted:  +{gain:.4f} AUC")

    # Optional: C sweep — refit on val scores, evaluate on cached test scores
    if args.C_sweep:
        from sklearn.linear_model import LogisticRegression
        val_scores_path = Path("ai_model/trained_models/val_scores.json")
        if not val_scores_path.exists():
            print("\n  (C-sweep skipped: val_scores.json not found)")
        else:
            with open(val_scores_path) as f:
                val_rows = json.load(f)
            val_detectors = [d for d in detector_names if d in val_rows[0]]
            if val_detectors != detector_names:
                print(f"\n  (C-sweep uses overlap of val+test detectors: {val_detectors})")
            X_val = np.array([[r[d] for d in val_detectors] for r in val_rows])
            y_val = np.array([r["label"] for r in val_rows])
            X_test = np.stack([arrays[d] for d in val_detectors], axis=1)
            print(f"\n{'='*60}\nC-SWEEP (refit on val, evaluate on test)\n{'='*60}")
            # Reference detector for the "vs X only" column (convnext > resnet50 > first available)
            ref_name = next((d for d in ("convnext", "resnet50", "laa", "clip") if d in val_detectors), val_detectors[0])
            ref_auc = results.get(f"{ref_name}_only", {}).get("auc", 0.0)
            coef_cols = " ".join(f"{d[:4]:>7}_w" for d in val_detectors)
            print(f"  {'C':>8}  {'test_AUC':>10}  {coef_cols}  vs {ref_name}")
            best = (None, 0.0)
            for C in [10.0, 1.0, 0.3, 0.1, 0.03, 0.01, 0.003, 0.001]:
                clf = LogisticRegression(C=C, max_iter=1000).fit(X_val, y_val)
                logit = clf.intercept_[0] + X_test @ clf.coef_[0]
                probs = 1.0 / (1.0 + np.exp(-logit))
                auc = roc_auc_score(y, probs)
                delta = auc - ref_auc
                sign = "+" if delta >= 0 else ""
                coef_str = " ".join(f"{c:>+7.3f}" for c in clf.coef_[0])
                print(f"  {C:>8.4f}  {auc:>10.4f}  {coef_str}  {sign}{delta:.4f}")
                if auc > best[1]:
                    best = (C, auc)
            print(f"\n  Best C on test: {best[0]} -> AUC {best[1]:.4f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump({
            "sample_size": len(y),
            "seed": args.seed,
            "coefficients": coefs,
            "intercept": intercept,
            "results": results,
            "auc_gain_learned_vs_unweighted": gain,
        }, f, indent=2)
    print(f"\n  Saved: {args.out}")


if __name__ == "__main__":
    main()
