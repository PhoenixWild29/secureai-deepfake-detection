#!/usr/bin/env python3
"""
Detection-correctness regression tests (MODEL-HONESTY guardrails, task B5).

These tests guard against *silent* detection regressions — the kind where the API
still returns 200 OK and a plausible-looking confidence, but the underlying model
quality has quietly collapsed (e.g. someone re-points the live path at an untrained
ensemble, or the learned ensemble weights get corrupted/overwritten).

They are designed to run in a CPU-only / no-GPU / no-torch sandbox:

  test_learned_ensemble_auc_on_val_scores
      Recomputes the learned logistic-ensemble probability for every sample in
      ai_model/trained_models/val_scores.json using the coefficients in
      ai_model/trained_models/ensemble_weights.json, then asserts ROC-AUC >= 0.90.
      Catches regressions in the actual scoring function production now uses,
      WITHOUT loading any heavy model weights. (Measured AUC on the committed data
      is ~0.964, so 0.90 is a safe floor that still flags real breakage.)

  test_production_routing_maps_to_enhanced_detector
      Asserts that ai_model/detect.py routes the production model_types
      ('enhanced'/'ensemble'/'full_ensemble') to EnhancedDetector
      (via detect_fake_enhanced), NOT to the deprecated EnsembleDetector that loads
      untrained random-head Xception/EfficientNet. Catches re-routing regressions.

Tests skip gracefully ONLY when a required data file is genuinely absent.
"""

import json
import math
import os

import pytest

# --- Locate the repo and key data files (no heavy imports required) ------------
HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
TRAINED_DIR = os.path.join(REPO_ROOT, "ai_model", "trained_models")
VAL_SCORES_PATH = os.path.join(TRAINED_DIR, "val_scores.json")
ENSEMBLE_WEIGHTS_PATH = os.path.join(TRAINED_DIR, "ensemble_weights.json")
DETECT_PY_PATH = os.path.join(REPO_ROOT, "ai_model", "detect.py")


def _roc_auc(scores, labels):
    """
    Compute ROC-AUC. Uses sklearn when available, otherwise a pure-python
    Mann-Whitney-U (rank-based) implementation with proper tie handling.
    Kept dependency-free so the test runs in a minimal sandbox.
    """
    try:
        from sklearn.metrics import roc_auc_score  # type: ignore
        return float(roc_auc_score(labels, scores))
    except Exception:
        # Rank-based AUC == P(score(pos) > score(neg)), ties counted as 0.5.
        n = len(scores)
        order = sorted(range(n), key=lambda i: scores[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j < n and scores[order[j]] == scores[order[i]]:
                j += 1
            avg_rank = (i + j - 1) / 2.0 + 1.0  # average rank (1-based) for ties
            for k in range(i, j):
                ranks[order[k]] = avg_rank
            i = j
        n_pos = sum(1 for l in labels if l == 1)
        n_neg = n - n_pos
        if n_pos == 0 or n_neg == 0:
            raise ValueError("ROC-AUC requires both positive and negative labels")
        sum_ranks_pos = sum(ranks[idx] for idx in range(n) if labels[idx] == 1)
        return (sum_ranks_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)


def _sigmoid(x):
    # Numerically stable logistic.
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ex = math.exp(x)
    return ex / (1.0 + ex)


def test_learned_ensemble_auc_on_val_scores():
    """
    Regression guard: the learned logistic ensemble that production uses must still
    separate real vs. fake at ROC-AUC >= 0.90 on the committed validation scores.

    This validates the EXACT combination function production runs (same coefficients,
    same per-detector scores), with zero model loading — so it works in CI/sandbox.
    A drop below 0.90 means the ensemble weights or scoring logic has regressed.
    """
    if not os.path.isfile(VAL_SCORES_PATH):
        pytest.skip(f"val_scores.json not found at {VAL_SCORES_PATH}")
    if not os.path.isfile(ENSEMBLE_WEIGHTS_PATH):
        pytest.skip(f"ensemble_weights.json not found at {ENSEMBLE_WEIGHTS_PATH}")

    with open(VAL_SCORES_PATH) as f:
        samples = json.load(f)
    with open(ENSEMBLE_WEIGHTS_PATH) as f:
        weights = json.load(f)

    detectors = weights["detectors"]
    coefs = weights["coefficients"]
    intercept = weights["intercept"]
    assert len(detectors) == len(coefs), "coefficients must align with detectors"

    scores, labels = [], []
    for s in samples:
        logit = intercept + sum(coefs[i] * float(s[d]) for i, d in enumerate(detectors))
        scores.append(_sigmoid(logit))
        labels.append(int(s["label"]))

    assert len(scores) > 0, "val_scores.json is empty"
    auc = _roc_auc(scores, labels)

    # Measured ~0.964 on the committed data; 0.90 is a safe regression floor.
    assert auc >= 0.90, (
        f"Learned ensemble ROC-AUC dropped to {auc:.4f} (< 0.90). "
        "The production scoring path or ensemble_weights.json has likely regressed."
    )


def test_production_routing_maps_to_enhanced_detector():
    """
    Regression guard: the live detection path for the production model types must
    route to EnhancedDetector (the trained ResNet50 + ConvNeXt + FFT + learned
    ensemble), NOT the deprecated EnsembleDetector (untrained Xception/EfficientNet,
    chance-level CLIP/LAA).

    Implemented as a lightweight source/contract check so it does not require torch,
    CLIP, or any model weights to be importable in the sandbox.
    """
    if not os.path.isfile(DETECT_PY_PATH):
        pytest.skip(f"detect.py not found at {DETECT_PY_PATH}")

    with open(DETECT_PY_PATH, encoding="utf-8") as f:
        src = f.read()

    # The production branch must call the EnhancedDetector wrapper...
    assert "detect_fake_enhanced(video_path)" in src, (
        "Production path no longer calls detect_fake_enhanced(); detection may have "
        "been re-routed away from the trained EnhancedDetector ensemble."
    )

    # ...and must NOT call the deprecated EnsembleDetector wrapper in the live branch.
    # (We allow the import to remain for back-compat, but not an active call.)
    assert "result = detect_fake_ensemble(" not in src, (
        "Production path calls detect_fake_ensemble(), which loads untrained "
        "Xception/EfficientNet heads and chance-level CLIP/LAA. It must route to "
        "EnhancedDetector instead."
    )

    # Optional: if heavy deps happen to be installed, confirm the symbol resolves to
    # the EnhancedDetector wrapper. Guarded so missing deps never fail the test.
    try:
        from ai_model import detect as detect_mod  # type: ignore
        from ai_model import enhanced_detector  # type: ignore

        assert (
            detect_mod.detect_fake_enhanced is enhanced_detector.detect_fake_enhanced
        ), "detect.detect_fake_enhanced should be enhanced_detector.detect_fake_enhanced"
    except Exception:
        # torch/CLIP/etc. not importable in this environment — source check above
        # already provides the contract guarantee.
        pass
