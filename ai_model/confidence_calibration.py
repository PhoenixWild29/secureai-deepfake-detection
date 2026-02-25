"""
Confidence calibration for deepfake detection outputs.

By default, "confidence" in API/detector responses is AGREEMENT STRENGTH:
  abs(ensemble_prob - 0.5) * 2  (how far from uncertain; 0 = uncertain, 1 = very decisive).
This is not statistically calibrated (i.e. "80% confident" does not mean 80% accuracy).

Optional calibration (temperature scaling or future Platt scaling) can be enabled
so the reported value better reflects reliability. See docs/guides/CONFIDENCE_CALIBRATION.md.
"""
import math
import os
from typing import Literal, Tuple

CalibrationMethod = Literal["agreement_strength", "temperature", "winning_prob"]


def agreement_strength(prob: float) -> float:
    """
    Distance from 0.5, scaled to [0, 1]. Not calibrated; use for "how decisive" only.
    """
    p = max(0.0, min(1.0, float(prob)))
    return abs(p - 0.5) * 2.0


def temperature_scale(prob: float, temperature: float) -> float:
    """
    Temperature scaling: logit = log(p/(1-p)), scaled = sigmoid(logit / T).
    T > 1 reduces overconfidence (pulls toward 0.5); T < 1 increases it.
    """
    p = max(1e-6, min(1.0 - 1e-6, float(prob)))
    T = max(0.1, float(temperature))
    logit = math.log(p / (1.0 - p))
    scaled_logit = logit / T
    return 1.0 / (1.0 + math.exp(-scaled_logit))


def confidence_from_ensemble(
    ensemble_prob: float,
    is_deepfake: bool,
    calibration: CalibrationMethod = "agreement_strength",
    temperature: float = 1.5,
) -> float:
    """
    Compute the single "confidence" value to report from ensemble probability.

    Args:
        ensemble_prob: Raw ensemble fake probability in [0, 1].
        is_deepfake: True if ensemble_prob > 0.5.
        calibration: 'agreement_strength' (default), 'temperature', or 'winning_prob'.
        temperature: Used when calibration == 'temperature' (e.g. 1.5 = less overconfident).

    Returns:
        Confidence in [0, 1]. For agreement_strength: 0 = uncertain, 1 = very decisive.
    """
    p = max(0.0, min(1.0, float(ensemble_prob)))
    if calibration == "agreement_strength":
        return agreement_strength(p)
    if calibration == "winning_prob":
        return p if is_deepfake else (1.0 - p)
    if calibration == "temperature":
        calibrated_p = temperature_scale(p, temperature)
        return calibrated_p if is_deepfake else (1.0 - calibrated_p)
    return agreement_strength(p)


def get_calibration_config() -> Tuple[CalibrationMethod, float]:
    """Read calibration method and temperature from environment."""
    method = (os.getenv("CONFIDENCE_CALIBRATION") or "agreement_strength").strip().lower()
    if method not in ("agreement_strength", "temperature", "winning_prob"):
        method = "agreement_strength"
    try:
        T = float(os.getenv("CONFIDENCE_TEMPERATURE", "1.5"))
    except (TypeError, ValueError):
        T = 1.5
    return method, T
