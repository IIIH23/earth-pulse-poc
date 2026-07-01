from earth_26s_detector import StationDetection, consensus_period


def detection(period_s: float, *, detected: bool = True) -> StationDetection:
    return StationDetection(
        code="XX.TEST",
        period_s=period_s,
        frequency_hz=1.0 / period_s,
        snr=4.0,
        detected=detected,
    )


def test_consensus_is_high_for_two_close_detections() -> None:
    period, confidence = consensus_period([detection(25.8), detection(26.2)])

    assert period == 26.0
    assert confidence.startswith("high")


def test_consensus_ignores_below_threshold_station() -> None:
    period, confidence = consensus_period(
        [detection(26.4), detection(24.0, detected=False)]
    )

    assert period == 26.4
    assert confidence.startswith("low")


def test_consensus_handles_no_detection() -> None:
    period, confidence = consensus_period([detection(26.0, detected=False)])

    assert period is None
    assert confidence.startswith("not detected")
