"""Refit the logistic-regression ensemble over per-detector scores.

The repo already ships a learned ensemble in
``ai_model/trained_models/ensemble_weights.json`` with this exact format::

    {
      "detectors": ["clip", "laa", "resnet50", "convnext", "fft"],
      "coefficients": [...],         # one per detector, same order
      "intercept": -1.2387,
      "C": 0.03,
      "test_auc_at_this_C": 0.9359...,
      "note": "..."
    }

This module reuses that mechanism but ADDS the new, better-generalizing
backbone as an extra detector column (``new_backbone``). It takes a table of
per-sample detector scores + labels, fits sklearn ``LogisticRegression`` with
the repo's ``C=0.03``, and writes a fresh ``ensemble_weights.json`` plus the
resulting test AUC.

Inputs accepted:
  * a CSV with columns = detector names + a ``label`` column, or
  * a json dict: {detector_name: [scores...], "label": [labels...]}.

The output preserves the existing detector order and appends new detectors so
the downstream inference code (which reads coefficients positionally) keeps
working for the old detectors.
"""

from __future__ import annotations

import json
import os
from typing import Dict, List, Optional, Sequence


# Canonical existing order from the repo's ensemble_weights.json.
EXISTING_DETECTORS: List[str] = ["clip", "laa", "resnet50", "convnext", "fft"]
NEW_BACKBONE_DETECTOR = "new_backbone"


# ---------------------------------------------------------------------------
# Loading score tables
# ---------------------------------------------------------------------------
def load_scores_csv(path: str, label_col: str = "label"):
    """Load a CSV of detector scores into (X, y, detector_names)."""
    import pandas as pd
    import numpy as np

    df = pd.read_csv(path)
    if label_col not in df.columns:
        raise ValueError(f"CSV must contain a '{label_col}' column.")
    detectors = [c for c in df.columns if c != label_col]
    X = df[detectors].to_numpy(dtype="float64")
    y = df[label_col].to_numpy(dtype="int64")
    return X, y, detectors


def load_scores_json(path: str, label_key: str = "label"):
    """Load a json dict {detector: [...], label: [...]} into (X, y, names)."""
    import numpy as np

    with open(path) as f:
        data = json.load(f)
    if label_key not in data:
        raise ValueError(f"json must contain a '{label_key}' key.")
    y = np.asarray(data[label_key], dtype="int64")
    detectors = [k for k in data.keys() if k != label_key]
    X = np.stack([np.asarray(data[d], dtype="float64") for d in detectors], axis=1)
    return X, y, detectors


def build_score_matrix(
    detector_scores: Dict[str, Sequence[float]],
    labels: Sequence[int],
    detector_order: Optional[List[str]] = None,
):
    """Assemble (X, y, names) from a dict of detector -> per-sample scores.

    All score arrays must be the same length and aligned to ``labels``. Missing
    detectors (e.g. CLIP/LAA not recomputed in this run) are NEUTRAL-FILLED with
    0.5 (chance) so the old coefficients still have a column position to attach
    to; this is a pragmatic choice so a refit can run with only a subset of
    detectors present. A neutral-filled (constant) column contributes ~nothing
    to the fit, effectively zeroing that detector's coefficient.
    """
    import numpy as np

    if detector_order is None:
        detector_order = EXISTING_DETECTORS + [NEW_BACKBONE_DETECTOR]
    y = np.asarray(labels, dtype="int64")
    n = len(y)
    cols = []
    for d in detector_order:
        if d in detector_scores and len(detector_scores[d]) == n:
            cols.append(np.asarray(detector_scores[d], dtype="float64"))
        else:
            # neutral fill: 0.5 (chance) so an absent detector contributes ~nothing
            cols.append(np.full(n, 0.5, dtype="float64"))
    X = np.stack(cols, axis=1)
    return X, y, list(detector_order)


# ---------------------------------------------------------------------------
# Refit
# ---------------------------------------------------------------------------
def refit_ensemble(
    X,
    y,
    detector_names: List[str],
    C: float = 0.03,
    out_path: Optional[str] = None,
    note: str = "",
) -> Dict:
    """Fit LogisticRegression(C) over detector scores; return weights dict.

    Mirrors the repo's existing ensemble_weights.json format so inference code
    can consume it unchanged. ``C=0.03`` matches the repo's chosen strength.
    """
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score

    y = np.asarray(y, dtype="int64")
    clf = LogisticRegression(C=C, max_iter=2000, solver="lbfgs")
    clf.fit(X, y)

    probs = clf.predict_proba(X)[:, 1]
    try:
        auc = float(roc_auc_score(y, probs)) if len(np.unique(y)) > 1 else float("nan")
    except Exception:
        auc = float("nan")

    weights = {
        "detectors": list(detector_names),
        "coefficients": [float(c) for c in clf.coef_.ravel().tolist()],
        "intercept": float(clf.intercept_.ravel()[0]),
        "C": float(C),
        "test_auc_at_this_C": auc,
        "note": note or (
            f"Refit including '{NEW_BACKBONE_DETECTOR}' over cross-dataset "
            f"scores (C={C})."
        ),
    }

    if out_path:
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(weights, f, indent=2)
        print(f"[ensemble_refit] wrote {out_path} (test AUC={auc:.4f})")
    return weights


def refit_from_eval_scores(
    scores_path: str,
    out_path: str,
    new_detector_name: str = NEW_BACKBONE_DETECTOR,
    C: float = 0.03,
    pool_datasets: bool = True,
) -> Dict:
    """Refit using the ``*_scores.json`` produced by evaluate.cross_dataset_report.

    Scores-file schema (per dataset)::

        {
          "<dataset>": {
            "paths":  [...],
            "labels": [0/1, ...],
            "probs":  [...],          # NEW backbone fake-prob (-> "new_backbone")
            "detectors": {            # OPTIONAL: real legacy detector columns
                "clip": [...], "laa": [...], "resnet50": [...],
                "convnext": [...], "fft": [...]   # any subset that was available
            }
          },
          ...
        }

    The new backbone column always comes from ``probs``. Each legacy detector
    listed under ``detectors`` contributes its REAL per-sample column. Any legacy
    detector that is ABSENT (the eval ran without it, or it failed to load) is
    handled cleanly by :func:`build_score_matrix`, which neutral-fills it with
    0.5 so the column position is preserved for the existing inference code.

    Backward compatibility: a sidecar with no ``detectors`` block (the old
    format) still works — every legacy column is then neutral-filled, exactly as
    before. Pooling all test datasets gives a single robust cross-dataset refit
    (set ``pool_datasets=False`` to use the first only).
    """
    import numpy as np

    with open(scores_path) as f:
        per_ds = json.load(f)

    all_probs: List[float] = []
    all_labels: List[int] = []
    # Accumulate legacy detector columns. We pool ACROSS datasets, so a legacy
    # detector is only usable as a real column if it is present for EVERY pooled
    # dataset (otherwise the pooled column would be ragged). Detectors missing
    # from any pooled dataset are dropped here and neutral-filled downstream.
    legacy_cols: Dict[str, List[float]] = {d: [] for d in EXISTING_DETECTORS}
    legacy_present_everywhere = {d: True for d in EXISTING_DETECTORS}

    n_pooled_datasets = 0
    for ds, d in per_ds.items():
        if not isinstance(d, dict) or "probs" not in d:
            continue
        n_probs = len(d["probs"])
        all_probs.extend(d["probs"])
        all_labels.extend(d["labels"])
        detectors_block = d.get("detectors") or {}
        for det in EXISTING_DETECTORS:
            col = detectors_block.get(det)
            if isinstance(col, list) and len(col) == n_probs:
                legacy_cols[det].extend(float(v) for v in col)
            else:
                # absent or length-mismatched for THIS dataset -> not usable
                legacy_present_everywhere[det] = False
        n_pooled_datasets += 1
        if not pool_datasets:
            break

    if not all_labels:
        raise RuntimeError(f"No usable scores in {scores_path}.")

    # Build the detector_scores dict with ONLY the legacy detectors that were
    # present (with the right length) across all pooled datasets; the rest are
    # left out and get neutral-filled by build_score_matrix.
    detector_scores: Dict[str, List[float]] = {new_detector_name: all_probs}
    used_legacy: List[str] = []
    filled_legacy: List[str] = []
    for det in EXISTING_DETECTORS:
        if (legacy_present_everywhere[det]
                and len(legacy_cols[det]) == len(all_labels)):
            detector_scores[det] = legacy_cols[det]
            used_legacy.append(det)
        else:
            filled_legacy.append(det)

    if used_legacy:
        print(f"[ensemble_refit] real legacy columns: {used_legacy}; "
              f"neutral-filled: {filled_legacy or 'none'}")
    else:
        print("[ensemble_refit] no real legacy columns found; all legacy "
              "detectors neutral-filled (re-run evaluate with "
              "compute_legacy_scores=True to populate them).")

    order = EXISTING_DETECTORS + [new_detector_name]
    X, y, names = build_score_matrix(detector_scores, all_labels, detector_order=order)

    if used_legacy:
        note = (f"Cross-dataset refit over {n_pooled_datasets} dataset(s). "
                f"Real columns: {used_legacy + [new_detector_name]}. "
                f"Neutral-filled (unavailable) legacy detectors: "
                f"{filled_legacy or 'none'}.")
    else:
        note = ("Cross-dataset refit. New backbone scores populated; legacy "
                "detectors neutral-filled (recompute CLIP/LAA/resnet50/convnext/"
                "fft on the same samples to give them real columns).")
    return refit_ensemble(X, y, names, C=C, out_path=out_path, note=note)
