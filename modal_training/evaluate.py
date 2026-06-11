"""Cross-dataset evaluation harness — the artifact that proves real progress.

MODEL_IMPROVEMENT_PLAN.md is explicit: in-domain accuracy is not how serious
deepfake detection is judged. What matters is CROSS-DATASET generalization —
train on one source (FF++), test on UNSEEN generators (Celeb-DF, DFDC). This
module computes, for each test dataset:

  * AUC (ROC area)
  * Average Precision (AP / PR-AUC)
  * EER (equal error rate) and its threshold
  * accuracy @ FPR = 0.10  (a product-relevant operating point)

plus a combined table. Results are written as json. sklearn is used when
available with a numpy fallback for AUC/AP/EER so the harness still runs in a
minimal environment.

Per-detector scores for a genuine ensemble refit
-------------------------------------------------
``cross_dataset_report`` ALSO records, per evaluation sample, the score from
every available LEGACY detector (clip/laa/resnet50/convnext/fft — recomputed via
``legacy_detectors.compute_detector_scores``) alongside the new backbone's score
and the ground-truth label. These are written to a ``*_scores.json`` sidecar in
the exact schema ``ensemble_refit.py`` consumes, so the ensemble can be refit
over REAL detector columns instead of neutral-filled 0.5 placeholders. Legacy
detectors that are unavailable are simply omitted (and neutral-filled later).

Public API
----------
compute_metrics(labels, probs) -> dict
evaluate_model(model, dataloader, device) -> dict
cross_dataset_report(model, config, datasets, out_path, *, compute_legacy_scores=True) -> dict
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Metric primitives (sklearn with numpy fallback)
# ---------------------------------------------------------------------------
def _roc_curve(labels, probs):
    """Return (fpr, tpr, thresholds). Uses sklearn if available."""
    import numpy as np
    try:
        from sklearn.metrics import roc_curve
        fpr, tpr, thr = roc_curve(labels, probs)
        return np.asarray(fpr), np.asarray(tpr), np.asarray(thr)
    except Exception:
        # numpy fallback: sort by score desc, sweep thresholds
        labels = np.asarray(labels)
        probs = np.asarray(probs)
        order = np.argsort(-probs)
        labels = labels[order]
        probs = probs[order]
        P = max(1, int(labels.sum()))
        N = max(1, int((1 - labels).sum()))
        tp = np.cumsum(labels)
        fp = np.cumsum(1 - labels)
        tpr = tp / P
        fpr = fp / N
        # prepend the (0,0) point
        fpr = np.concatenate([[0.0], fpr])
        tpr = np.concatenate([[0.0], tpr])
        thr = np.concatenate([[np.inf], probs])
        return fpr, tpr, thr


def _auc_from_curve(fpr, tpr) -> float:
    import numpy as np
    return float(np.trapz(tpr, fpr))


def compute_auc(labels, probs) -> float:
    import numpy as np
    try:
        from sklearn.metrics import roc_auc_score
        if len(np.unique(labels)) < 2:
            return float("nan")
        return float(roc_auc_score(labels, probs))
    except Exception:
        fpr, tpr, _ = _roc_curve(labels, probs)
        return _auc_from_curve(fpr, tpr)


def compute_ap(labels, probs) -> float:
    import numpy as np
    try:
        from sklearn.metrics import average_precision_score
        if len(np.unique(labels)) < 2:
            return float("nan")
        return float(average_precision_score(labels, probs))
    except Exception:
        # crude PR-AUC via trapezoid over sorted recall
        labels = np.asarray(labels)
        probs = np.asarray(probs)
        order = np.argsort(-probs)
        labels = labels[order]
        tp = np.cumsum(labels)
        fp = np.cumsum(1 - labels)
        P = max(1, int(labels.sum()))
        precision = tp / np.maximum(1, tp + fp)
        recall = tp / P
        return float(np.trapz(precision, recall))


def compute_eer(labels, probs) -> Tuple[float, float]:
    """Equal Error Rate and its threshold (where FPR == FNR)."""
    import numpy as np
    fpr, tpr, thr = _roc_curve(labels, probs)
    fnr = 1.0 - tpr
    # index where |fpr - fnr| is minimal
    idx = int(np.nanargmin(np.abs(fpr - fnr)))
    eer = float((fpr[idx] + fnr[idx]) / 2.0)
    threshold = float(thr[idx]) if np.isfinite(thr[idx]) else 0.5
    return eer, threshold


def accuracy_at_fpr(labels, probs, target_fpr: float = 0.10) -> Dict[str, float]:
    """Accuracy at the threshold giving FPR closest to ``target_fpr``."""
    import numpy as np
    fpr, tpr, thr = _roc_curve(labels, probs)
    idx = int(np.nanargmin(np.abs(fpr - target_fpr)))
    threshold = float(thr[idx]) if np.isfinite(thr[idx]) else 0.5
    preds = (np.asarray(probs) >= threshold).astype(int)
    labels = np.asarray(labels).astype(int)
    acc = float((preds == labels).mean())
    return {"acc": acc, "threshold": threshold,
            "achieved_fpr": float(fpr[idx]), "tpr_at_fpr": float(tpr[idx])}


def compute_metrics(labels, probs) -> Dict[str, float]:
    """All headline metrics for one (labels, probs) pair."""
    import numpy as np
    labels = np.asarray(labels)
    probs = np.asarray(probs)
    eer, eer_thr = compute_eer(labels, probs)
    at_fpr = accuracy_at_fpr(labels, probs, 0.10)
    # plain accuracy at 0.5 for reference
    acc05 = float(((probs >= 0.5).astype(int) == labels.astype(int)).mean())
    return {
        "auc": compute_auc(labels, probs),
        "ap": compute_ap(labels, probs),
        "eer": eer,
        "eer_threshold": eer_thr,
        "acc_at_fpr10": at_fpr["acc"],
        "threshold_at_fpr10": at_fpr["threshold"],
        "acc_at_0.5": acc05,
        "n": int(len(labels)),
        "n_pos": int(labels.sum()),
    }


# ---------------------------------------------------------------------------
# Model evaluation
# ---------------------------------------------------------------------------
def _infer_probs(model, dataloader, device) -> Tuple[list, list, list]:
    """Run the model over a dataloader -> (labels, probs, paths)."""
    import numpy as np
    import torch

    model.eval()
    all_probs, all_labels, all_paths = [], [], []
    with torch.no_grad():
        for batch in dataloader:
            if len(batch) == 3:
                x, y, paths = batch
            else:
                x, y = batch[0], batch[1]
                paths = [""] * len(y)
            x = x.to(device, non_blocking=True)
            with torch.cuda.amp.autocast(enabled=torch.cuda.is_available()):
                logits = model(x).squeeze(-1)
            probs = torch.sigmoid(logits).float().cpu().numpy()
            all_probs.append(probs)
            all_labels.append(y.numpy())
            all_paths.extend(list(paths))
    return (np.concatenate(all_labels).tolist(),
            np.concatenate(all_probs).tolist(),
            all_paths)


def evaluate_model(model, dataloader, device: Optional[str] = None) -> Dict:
    """Evaluate ``model`` on a dataloader; return metrics + raw scores.

    The raw per-sample scores are returned so they can be fed to the ensemble
    refit (ensemble_refit.py) as the new backbone's detector column.
    """
    import torch
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    labels, probs, paths = _infer_probs(model, dataloader, device)
    metrics = compute_metrics(labels, probs)
    return {"metrics": metrics, "labels": labels, "probs": probs, "paths": paths}


def _legacy_detector_scores(image_paths: List[str], device: str) -> Dict[str, list]:
    """Recompute available legacy detector scores for ``image_paths``.

    Thin, defensive wrapper around ``legacy_detectors.compute_detector_scores``
    so that a missing module / dependency degrades to an EMPTY dict (legacy
    columns then get neutral-filled at refit time) instead of crashing the eval.
    Returns ``{detector_key: [score, ...]}`` for every detector that succeeded,
    each list aligned 1:1 with ``image_paths``.
    """
    if not image_paths:
        return {}
    try:
        from .legacy_detectors import compute_detector_scores
    except Exception as exc:  # module import problem
        print(f"[evaluate] legacy_detectors unavailable ({exc}); "
              f"legacy columns will be neutral-filled at refit.")
        return {}
    try:
        arrays = compute_detector_scores(image_paths, device=device)
    except Exception as exc:  # never let detector scoring break the eval
        print(f"[evaluate] legacy detector scoring failed ({exc}); "
              f"legacy columns will be neutral-filled at refit.")
        return {}
    # Convert numpy arrays -> plain lists for json serialisation.
    return {k: [float(v) for v in arr] for k, arr in arrays.items()}


def cross_dataset_report(model, config, datasets: List[str],
                         out_path: str,
                         compute_legacy_scores: bool = True) -> Dict:
    """Evaluate a trained model across multiple UNSEEN datasets.

    Builds a no-aug eval dataloader per dataset (from extracted crops), computes
    the full metric set, and writes a combined json report. Returns the report
    dict. This is the cross-dataset AUC table from the improvement plan.

    Per-detector scores (genuine ensemble refit)
    --------------------------------------------
    When ``compute_legacy_scores`` is True (default), this ALSO recomputes each
    available legacy detector's per-sample score over the SAME crops and records
    them in the ``*_scores.json`` sidecar. The sidecar schema, per dataset::

        {
          "<dataset>": {
            "paths":  [...],            # crop path per sample
            "labels": [0/1, ...],       # ground-truth label per sample
            "probs":  [...],            # NEW backbone fake-prob (== "new_backbone")
            "detectors": {              # legacy detector columns, when available
                "clip": [...], "laa": [...], "resnet50": [...],
                "convnext": [...], "fft": [...]
            }
          },
          ...
        }

    Any legacy detector that is unavailable is simply absent from ``detectors``;
    ``ensemble_refit`` neutral-fills the missing columns. Set
    ``compute_legacy_scores=False`` to skip the (heavy) recompute — the sidecar
    then contains only the new-backbone ``probs`` and legacy columns are
    neutral-filled, reproducing the prior behaviour.
    """
    import torch
    from .dataset import build_eval_dataloader

    device = "cuda" if torch.cuda.is_available() else "cpu"
    report: Dict[str, Dict] = {
        "backbone": getattr(config, "backbone", "unknown"),
        "train_datasets": config.train_datasets,
        "per_dataset": {},
        "scores": {},  # dataset -> {paths, labels, probs, detectors} for ensemble refit
    }

    for ds in datasets:
        try:
            loader, _samples = build_eval_dataloader(config, ds)
        except Exception as exc:
            print(f"[evaluate] skipping {ds}: {exc}")
            report["per_dataset"][ds] = {"error": str(exc)}
            continue
        result = evaluate_model(model, loader, device)
        report["per_dataset"][ds] = result["metrics"]

        ds_scores: Dict[str, object] = {
            "paths": result["paths"],
            "labels": result["labels"],
            "probs": result["probs"],  # the new backbone's column
        }
        # Recompute REAL legacy detector columns over the same crops so the
        # ensemble refit fits over real signal rather than 0.5 neutral-fill.
        if compute_legacy_scores:
            legacy = _legacy_detector_scores(result["paths"], device)
            if legacy:
                ds_scores["detectors"] = legacy
                print(f"[evaluate] {ds}: legacy detectors scored -> "
                      f"{sorted(legacy.keys())}")
            else:
                print(f"[evaluate] {ds}: no legacy detector columns "
                      f"(will be neutral-filled at refit).")
        report["scores"][ds] = ds_scores

        m = result["metrics"]
        print(f"[evaluate] {ds}: AUC={m['auc']:.4f} AP={m['ap']:.4f} "
              f"EER={m['eer']:.4f} acc@FPR10={m['acc_at_fpr10']:.4f} (n={m['n']})")

    # combined macro average over datasets that succeeded
    aucs = [v["auc"] for v in report["per_dataset"].values()
            if isinstance(v, dict) and "auc" in v and v["auc"] == v["auc"]]
    report["mean_cross_dataset_auc"] = (sum(aucs) / len(aucs)) if aucs else None

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    # write the report WITHOUT the bulky per-sample scores in the main file;
    # keep scores in a sibling file for the ensemble step.
    main = {k: v for k, v in report.items() if k != "scores"}
    with open(out_path, "w") as f:
        json.dump(main, f, indent=2, default=str)
    scores_path = out_path.replace(".json", "_scores.json")
    with open(scores_path, "w") as f:
        json.dump(report["scores"], f, default=str)
    report["_report_path"] = out_path
    report["_scores_path"] = scores_path
    print(f"[evaluate] wrote {out_path} (mean cross-dataset AUC="
          f"{report['mean_cross_dataset_auc']})")
    return report
