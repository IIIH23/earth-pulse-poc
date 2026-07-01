import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from earth_26s_detector import Microseism26sResult, StationDetection
from generate_earth_pulse_json import build_payload


ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads(
    (ROOT / "contracts" / "earth-pulse.schema.json").read_text(encoding="utf-8")
)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def assert_valid(payload: dict) -> None:
    errors = sorted(VALIDATOR.iter_errors(payload), key=lambda error: list(error.path))
    assert not errors, "\n".join(
        f"{'/'.join(map(str, error.path)) or '<root>'}: {error.message}"
        for error in errors
    )


def confirmed_result() -> Microseism26sResult:
    stations = [
        StationDetection("II.SHEL", 25.9, 1.0 / 25.9, 5.0, True),
        StationDetection("IU.TSUM", 26.1, 1.0 / 26.1, 4.2, True),
    ]
    return Microseism26sResult(
        detected_any=True,
        consensus_period_s=26.0,
        consensus_frequency_hz=1.0 / 26.0,
        confidence_label="high (multiple stations, tight agreement)",
        stations_detected=2,
        stations_attempted=2,
        per_station=stations,
        timestamp_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def test_published_feed_matches_schema() -> None:
    payload = json.loads((ROOT / "earth-pulse.json").read_text(encoding="utf-8"))
    assert_valid(payload)


def test_application_fixture_matches_schema() -> None:
    payload = json.loads(
        (
            ROOT
            / "apps"
            / "pulse-of-earth"
            / "fixtures"
            / "earth-pulse.sample.json"
        ).read_text(encoding="utf-8")
    )
    assert_valid(payload)


def test_generated_confirmed_payload_matches_schema() -> None:
    payload = build_payload(
        confirmed_result(),
        hours=6.0,
        snr_threshold=3.0,
        previous={},
        history_limit=24,
    )

    assert payload["app_pulse"]["source"] == "current_measurement"
    assert payload["breathing_rhythm"]["locked"] is True
    assert_valid(payload)
