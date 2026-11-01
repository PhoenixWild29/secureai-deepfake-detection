"""Completed-job report stored on the job row.

The worker writes a short JSON document into ``detail`` when the detector
returns signals. Failure text stays the fixed public message and does not
parse as a report.

The API renders those fields to PDF with fpdf2 (``app.pdf_report``). This
package does not import a PDF library, so the worker does not install one.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping

from secureai_shared.attestation import may_issue_attestation

REPORT_VERSION = 1

LIMITATIONS = (
    "This score is a CPU heuristic. It is not a trained deepfake classifier, "
    "not a benchmarked accuracy figure, and not legal evidence that a clip is "
    "real or synthetic."
)


def dump_report_detail(model: str, signals: Mapping[str, float]) -> str:
    """Serialize model name and 0..1 signals. Rejects empty or non-finite input."""

    if not model or not signals:
        raise ValueError("report detail needs a model and at least one signal")
    cleaned: dict[str, float] = {}
    for key, value in signals.items():
        if not isinstance(key, str) or not key:
            raise ValueError("signal name must be text")
        number = float(value)
        if not math.isfinite(number) or not 0.0 <= number <= 1.0:
            raise ValueError("signal out of range")
        cleaned[key] = round(number, 4)
    payload = {"model": model, "signals": cleaned, "v": REPORT_VERSION}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def may_export_pdf(*, auth_mode: str, quota_mode: str, plan: str) -> bool:
    """Pro and Team can download a PDF. A free plan cannot.

    This is ``may_issue_attestation``, including the private dev workstation
    with unlimited quota. ``AUTH_MODE=clerk`` stays on the plan check even
    when quotas are unlimited, so Free cannot export. ``past_due`` is already
    folded into ``plan`` by ``effective_plan``.
    """

    return may_issue_attestation(auth_mode=auth_mode, quota_mode=quota_mode, plan=plan)


def load_report_detail(detail: str | None) -> tuple[str | None, dict[str, float]]:
    """Return ``(model, signals)``. Plain failure text yields ``(None, {})``."""

    if not detail:
        return None, {}
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        return None, {}
    if not isinstance(payload, dict) or payload.get("v") != REPORT_VERSION:
        return None, {}
    model = payload.get("model")
    raw = payload.get("signals")
    if not isinstance(model, str) or not model or not isinstance(raw, dict):
        return None, {}
    signals: dict[str, float] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, (int, float)) and not isinstance(value, bool):
            signals[key] = float(value)
    if not signals:
        return None, {}
    return model, signals
