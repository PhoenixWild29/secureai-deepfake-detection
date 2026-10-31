from detector import detect_video


def test_detect_video_does_not_need_a_file() -> None:
    result = detect_video("missing-clip.mp4")
    assert result["prediction"] in {"real", "fake"}
    assert 0.5 <= result["confidence"] <= 0.99


def test_detect_video_is_stable() -> None:
    assert detect_video("clip.mp4") == detect_video("clip.mp4")
