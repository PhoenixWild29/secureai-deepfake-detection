#!/usr/bin/env python3
"""
Full Celeb-DF v2 benchmark — runs the ensemble on all 518 official test videos.
Reports AUC, Acc, F1, EER per detector (clip, laa, resnet50) + ensemble.
Results saved to benchmark_results/celeb_df_v2_full_<timestamp>.json
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.metrics import (accuracy_score, f1_score, precision_score,
                             recall_score, roc_auc_score, roc_curve)

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def _eer(y_true, y_scores):
    fpr, tpr, thresholds = roc_curve(y_true, y_scores)
    fnr = 1.0 - tpr
    idx = np.argmin(np.abs(fpr - fnr))
    return float((fpr[idx] + fnr[idx]) / 2.0), float(thresholds[idx])


def metrics(name, y, scores):
    preds = (np.array(scores) > 0.5).astype(int)
    auc = roc_auc_score(y, scores)
    eer, eer_t = _eer(y, scores)
    return {
        "name": name,
        "auc_roc": auc,
        "eer": eer,
        "eer_threshold": eer_t,
        "accuracy": accuracy_score(y, preds),
        "precision": precision_score(y, preds, zero_division=0),
        "recall": recall_score(y, preds, zero_division=0),
        "f1": f1_score(y, preds, zero_division=0),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-root", default="datasets/celeb_df_v2/test")
    parser.add_argument("--num-frames", type=int, default=16)
    parser.add_argument("--out-dir", default="benchmark_results")
    args = parser.parse_args()

    test_root = Path(args.test_root)
    real = sorted((test_root / "real").glob("*.mp4"))
    fake = sorted((test_root / "fake").glob("*.mp4"))
    videos = [(p, 0) for p in real] + [(p, 1) for p in fake]
    print(f"Benchmark: {len(real)} real + {len(fake)} fake = {len(videos)} videos")
    print(f"Frames per video: {args.num_frames}")

    print("Loading EnhancedDetector ...")
    from ai_model.enhanced_detector import EnhancedDetector
    det = EnhancedDetector()
    print(f"  laa_available:      {det.laa_available}")
    print(f"  resnet50_available: {det.resnet50_available}")
    print(f"  ensemble_weights:   {'loaded' if det.ensemble_weights else 'none (unweighted)'}\n")

    rows = []
    errors = 0
    t0 = time.time()
    for i, (vid, label) in enumerate(videos, 1):
        try:
            r = det.detect(str(vid), num_frames=args.num_frames)
            rows.append({
                "video": vid.name,
                "label": label,
                "ensemble": r["ensemble_fake_probability"],
                "clip": r["clip_fake_probability"],
                "laa": r["laa_fake_probability"],
                "resnet50": r["resnet50_fake_probability"],
                "convnext": r.get("convnext_fake_probability", 0.5),
                "fft":      r.get("fft_fake_probability", 0.5),
                "method": r["method"],
            })
        except Exception as e:
            errors += 1
            print(f"\n  [!] {vid.name}: {e}")

        if i % 10 == 0 or i == len(videos):
            elapsed = time.time() - t0
            eta = elapsed / i * (len(videos) - i)
            print(f"  [{i}/{len(videos)}]  {elapsed:.0f}s elapsed  ETA {eta:.0f}s", flush=True)

    if len(rows) < 2:
        print("ERROR: too few successful predictions")
        sys.exit(1)

    y   = np.array([r["label"]    for r in rows])
    ens = np.array([r["ensemble"] for r in rows])
    clip = np.array([r["clip"]    for r in rows])
    laa = np.array([r["laa"]      for r in rows])
    res = np.array([r["resnet50"] for r in rows])

    results = {
        "ensemble":  metrics("ensemble",  y, ens),
        "resnet50":  metrics("resnet50",  y, res),
        "clip":      metrics("clip",      y, clip),
        "laa":       metrics("laa",       y, laa),
        "unweighted_mean": metrics("unweighted_mean", y, (clip + laa + res) / 3.0),
    }

    print("\n" + "=" * 70)
    print(f"CELEB-DF v2 FULL BENCHMARK ({len(rows)} videos, {errors} errors)")
    print("=" * 70)
    print(f"  {'Detector':<18} {'AUC':>8} {'EER':>8} {'Acc':>8} {'F1':>8}")
    for k in ("ensemble", "resnet50", "unweighted_mean", "clip", "laa"):
        m = results[k]
        print(f"  {k:<18} {m['auc_roc']:>8.4f} {m['eer']:>8.4f} {m['accuracy']:>8.4f} {m['f1']:>8.4f}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"celeb_df_v2_full_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump({
            "timestamp": timestamp,
            "num_videos": len(rows),
            "num_errors": errors,
            "num_frames_per_video": args.num_frames,
            "weighted_ensemble": det.ensemble_weights is not None,
            "ensemble_weights": det.ensemble_weights,
            "metrics": results,
            "predictions": rows,
            "total_time_seconds": time.time() - t0,
        }, f, indent=2)
    print(f"\n  Saved: {out_path}")


if __name__ == "__main__":
    main()
