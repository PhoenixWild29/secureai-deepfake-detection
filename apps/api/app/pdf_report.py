"""One-page PDF for a completed detection report.

fpdf2 writes the page with the built-in Helvetica font. There is no browser
and no chart. Characters outside Windows-1252 become ``?`` so an unusual
filename cannot fail the download.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone

from fpdf import FPDF

PDF_PLAN_REQUIRED = "PDF export requires a Pro or Team plan."

_SIGNAL_ORDER = ("texture", "motion", "temporal", "region")
_SIGNAL_LABELS = {
    "texture": "Texture",
    "motion": "Motion",
    "temporal": "Temporal",
    "region": "Region",
}


def render_job_report_pdf(
    *,
    job_id: str,
    org_id: str | None,
    filename: str,
    status: str,
    prediction: str | None,
    confidence: float | None,
    model: str | None,
    signals: Mapping[str, float],
    created_at: datetime,
    updated_at: datetime,
    limitations: str,
) -> bytes:
    """Render the JSON report fields. A typical job stays on one page."""

    pdf = FPDF(format="A4")
    pdf.set_title("SecureAI Detection Report")
    pdf.set_author("SecureAI")
    pdf.set_creator("SecureAI")
    pdf.set_subject(job_id)
    pdf.set_margins(18, 18, 18)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "SecureAI Detection Report", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    rows = (
        ("Job", job_id),
        ("Organization", org_id if org_id else "n/a"),
        ("File", filename),
        ("Status", status),
        ("Prediction", prediction if prediction else "n/a"),
        ("Confidence", _confidence(confidence)),
        ("Model", model if model else "n/a"),
        ("Created", _iso(created_at)),
        ("Updated", _iso(updated_at)),
    )
    for label, value in rows:
        _row(pdf, label, value)

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Signals", new_x="LMARGIN", new_y="NEXT")
    ordered = _ordered_signals(signals)
    if not ordered:
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 7, "No signals stored.", new_x="LMARGIN", new_y="NEXT")
    else:
        for name in ordered:
            _row(pdf, _signal_label(name), _number(signals[name]))

    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Limitations", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 5, _pdf_text(limitations), align="LEFT", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def _row(pdf: FPDF, label: str, value: str) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(42, 7, _pdf_text(label), new_x="RIGHT", new_y="TOP")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 7, _pdf_text(value), align="LEFT", new_x="LMARGIN", new_y="NEXT")


def _ordered_signals(signals: Mapping[str, float]) -> list[str]:
    preferred = [name for name in _SIGNAL_ORDER if name in signals]
    rest = sorted(name for name in signals if name not in _SIGNAL_ORDER)
    return preferred + rest


def _signal_label(name: str) -> str:
    return _SIGNAL_LABELS.get(name, name)


def _confidence(value: float | None) -> str:
    if value is None:
        return "n/a"
    percent = f"{value * 100:.1f}".rstrip("0").rstrip(".")
    return f"{_number(value)} ({percent}%)"


def _number(value: float) -> str:
    return json.dumps(float(value))


def _iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat()


def _pdf_text(value: str) -> str:
    return value.encode("cp1252", "replace").decode("cp1252")
