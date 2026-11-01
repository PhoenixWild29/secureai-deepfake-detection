import json

from secureai_shared.report import LIMITATIONS, dump_report_detail, load_report_detail
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


def test_dump_rejects_out_of_range_signals() -> None:
    try:
        dump_report_detail("cpu-multisignal-v1", {"texture": 1.2})
    except ValueError:
        return
    raise AssertionError("expected ValueError")
