import json

from secureai_shared.attestation import may_issue_attestation
from secureai_shared.report import LIMITATIONS, dump_report_detail, load_report_detail, may_export_pdf
from secureai_shared.store import PUBLIC_FAILURE_DETAIL


def test_report_detail_round_trip() -> None:
    raw = dump_report_detail(
        "cpu-multisignal-v1",
        {"texture": 0.125, "motion": 0, "temporal": 1, "region": 0.33336},
    )
    model, signals = load_report_detail(raw)
    assert model == "cpu-multisignal-v1"
    assert signals["texture"] == 0.125
    assert signals["region"] == 0.3334
    assert "heuristic" in LIMITATIONS
    parsed = json.loads(raw)
    assert parsed["v"] == 1


def test_failure_text_is_not_a_report() -> None:
    assert load_report_detail(None) == (None, {})
    assert load_report_detail(PUBLIC_FAILURE_DETAIL) == (None, {})
    assert load_report_detail("{") == (None, {})


def test_pdf_plan_matches_attestation() -> None:
    cases = [
        ("clerk", "enforce", "free"),
        ("clerk", "enforce", "pro"),
        ("clerk", "enforce", "team"),
        ("clerk", "unlimited", "free"),
        ("clerk", "unlimited", "pro"),
        ("dev", "unlimited", "free"),
        ("dev", "enforce", "free"),
        ("dev", "enforce", "team"),
    ]
    for auth_mode, quota_mode, plan in cases:
        assert may_export_pdf(auth_mode=auth_mode, quota_mode=quota_mode, plan=plan) is may_issue_attestation(
            auth_mode=auth_mode, quota_mode=quota_mode, plan=plan
        )


def test_dump_rejects_out_of_range_signals() -> None:
    try:
        dump_report_detail("cpu-multisignal-v1", {"texture": 1.2})
    except ValueError:
        return
    raise AssertionError("expected ValueError")
