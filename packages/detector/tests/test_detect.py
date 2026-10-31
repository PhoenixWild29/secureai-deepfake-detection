from detector import detect_video


def test_stub_does_not_need_a_file() -> None:
    result = detect_video("missing-clip.mp4", mode="stub")
    assert result["prediction"] in {"real", "fake"}
    assert 0.5 <= result["confidence"] <= 0.99


def test_stub_is_stable() -> None:
    assert detect_video("clip.mp4", mode="stub") == detect_video("clip.mp4", mode="stub")


def test_unknown_mode_is_rejected() -> None:
    try:
        detect_video("clip.mp4", mode="gpu")
    except ValueError as exc:
        assert "gpu" in str(exc)
    else:
        raise AssertionError("expected ValueError")
