#!/usr/bin/env python3
"""Generate the public Earth Pulse JSON consumed by the app."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np

from earth_26s_detector import (
    BACKGROUND_BANDS_HZ,
    DEFAULT_DETECT_SNR,
    DEFAULT_HOURS,
    TARGET_CENTER_HZ,
    TARGET_HIGH_HZ,
    TARGET_LOW_HZ,
    Microseism26sResult,
    detect_26s_microseism,
)


SCHEMA_VERSION = "1.0.0"
BASELINE_PERIOD_S = 26.0
BREATHING_INHALE_S = 13.0
BREATHING_EXHALE_S = 13.0
DEFAULT_OUTPUT = Path("earth-pulse.json")
DEFAULT_SEED_JOURNAL = Path("earth_26s_runs.jsonl")
DEFAULT_HISTORY_LIMIT = 24

STATION_LABELS = {
    "II.SHEL": "St. Helena, South Atlantic",
    "II.ASCN": "Ascension Island, South Atlantic",
    "II.BFO": "Black Forest, Germany",
    "II.MBAR": "Mbarara, Uganda",
    "IU.TSUM": "Tsumeb, Namibia",
    "IU.ANMO": "Albuquerque, New Mexico",
}


def _finite(value: float | None) -> float | None:
    if value is None or np.isnan(value):
        return None
    return float(value)


def _load_previous(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _load_seed_journal(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return records


def _station_from_journal_record(record: dict[str, Any]) -> dict[str, Any] | None:
    best_code = record.get("best_station")
    stations = record.get("per_station") or []
    for station in stations:
        if station.get("code") == best_code:
            return {
                "code": station.get("code"),
                "label": STATION_LABELS.get(station.get("code"), station.get("code")),
                "period_s": _finite(station.get("period_s")),
                "frequency_hz": _finite(station.get("frequency_hz")),
                "snr": _finite(station.get("snr")),
                "detected": bool(station.get("detected")),
                "error": station.get("error"),
            }

    if best_code:
        return {
            "code": best_code,
            "label": STATION_LABELS.get(best_code, best_code),
            "period_s": None,
            "frequency_hz": None,
            "snr": _finite(record.get("best_snr")),
            "detected": True,
            "error": None,
        }
    return None


def _last_good_from_journal(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    for record in reversed(records):
        period = _finite(record.get("consensus_period_s"))
        frequency = _finite(record.get("consensus_frequency_hz"))
        if int(record.get("stations_detected") or 0) < 2 or period is None or frequency is None:
            continue

        return {
            "measured_at_utc": record.get("timestamp_utc"),
            "period_s": period,
            "frequency_hz": frequency,
            "confidence_label": record.get("confidence_label"),
            "stations_detected": int(record.get("stations_detected") or 0),
            "stations_attempted": int(record.get("stations_attempted") or 0),
            "best_station": _station_from_journal_record(record),
            "median_snr": _finite(record.get("median_snr")),
        }
    return None


def _history_from_journal(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    history = []
    for record in records:
        best_code = record.get("best_station")
        stations_detected = int(record.get("stations_detected") or 0)
        period = _finite(record.get("consensus_period_s"))
        if stations_detected >= 2 and period is not None:
            quality_status = "confirmed"
        elif bool(record.get("detected_any")) and period is not None:
            quality_status = "weak_single_station"
        else:
            quality_status = "not_detected"

        history.append(
            {
                "measured_at_utc": record.get("timestamp_utc"),
                "quality_status": quality_status,
                "detected": bool(record.get("detected_any")),
                "period_s": period,
                "frequency_hz": _finite(record.get("consensus_frequency_hz")),
                "stations_detected": stations_detected,
                "stations_attempted": int(record.get("stations_attempted") or 0),
                "best_station_code": best_code,
                "best_snr": _finite(record.get("best_snr")),
                "median_snr": _finite(record.get("median_snr")),
            }
        )
    return history


def _seed_previous_from_journal(
    previous: dict[str, Any],
    journal_records: list[dict[str, Any]],
    history_limit: int,
) -> dict[str, Any]:
    if not journal_records:
        return previous

    seeded = dict(previous)
    if not seeded.get("last_good_measurement"):
        seeded["last_good_measurement"] = _last_good_from_journal(journal_records)

    seed_history = _history_from_journal(journal_records)
    existing_history = seeded.get("history") or []
    merged_history: list[dict[str, Any]] = []
    seen_times = set()
    for item in [*seed_history, *existing_history]:
        measured_at = item.get("measured_at_utc")
        if measured_at in seen_times:
            continue
        seen_times.add(measured_at)
        merged_history.append(item)
    if merged_history:
        seeded["history"] = merged_history[-history_limit:]
    return seeded


def _station_records(result: Microseism26sResult) -> list[dict[str, Any]]:
    records = []
    for detection in result.per_station:
        station = asdict(detection)
        station["label"] = STATION_LABELS.get(detection.code, detection.code)
        station["period_s"] = _finite(detection.period_s)
        station["frequency_hz"] = _finite(detection.frequency_hz)
        station["snr"] = _finite(detection.snr)
        records.append(station)
    return records


def _best_station(stations: list[dict[str, Any]]) -> dict[str, Any] | None:
    candidates = [station for station in stations if station.get("snr") is not None]
    if not candidates:
        return None
    return max(candidates, key=lambda station: float(station["snr"]))


def _quality_status(result: Microseism26sResult) -> str:
    if result.stations_detected >= 2 and result.consensus_period_s is not None:
        return "confirmed"
    if result.detected_any and result.consensus_period_s is not None:
        return "weak_single_station"
    return "not_detected"


def _current_measurement(
    result: Microseism26sResult,
    hours: float,
    snr_threshold: float,
) -> dict[str, Any]:
    stations = _station_records(result)
    best = _best_station(stations)
    snrs = [float(station["snr"]) for station in stations if station.get("snr") is not None]

    return {
        "measured_at_utc": result.timestamp_utc.isoformat(),
        "window_hours": hours,
        "target_frequency_hz": TARGET_CENTER_HZ,
        "target_period_s": BASELINE_PERIOD_S,
        "target_band_hz": [TARGET_LOW_HZ, TARGET_HIGH_HZ],
        "background_bands_hz": [list(band) for band in BACKGROUND_BANDS_HZ],
        "snr_threshold": snr_threshold,
        "detected": result.detected_any,
        "quality_status": _quality_status(result),
        "confidence_label": result.confidence_label,
        "period_s": _finite(result.consensus_period_s),
        "frequency_hz": _finite(result.consensus_frequency_hz),
        "stations_detected": result.stations_detected,
        "stations_attempted": result.stations_attempted,
        "station_errors": sum(1 for station in stations if station.get("error")),
        "best_station": best,
        "median_snr": float(np.median(snrs)) if snrs else None,
        "stations": stations,
    }


def _history_record(measurement: dict[str, Any]) -> dict[str, Any]:
    best = measurement.get("best_station") or {}
    return {
        "measured_at_utc": measurement["measured_at_utc"],
        "quality_status": measurement["quality_status"],
        "detected": measurement["detected"],
        "period_s": measurement["period_s"],
        "frequency_hz": measurement["frequency_hz"],
        "stations_detected": measurement["stations_detected"],
        "stations_attempted": measurement["stations_attempted"],
        "best_station_code": best.get("code"),
        "best_snr": best.get("snr"),
        "median_snr": measurement["median_snr"],
    }


def _select_app_pulse(
    current: dict[str, Any],
    previous: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if current["quality_status"] == "confirmed":
        last_good = {
            "measured_at_utc": current["measured_at_utc"],
            "period_s": current["period_s"],
            "frequency_hz": current["frequency_hz"],
            "confidence_label": current["confidence_label"],
            "stations_detected": current["stations_detected"],
            "stations_attempted": current["stations_attempted"],
            "best_station": current["best_station"],
            "median_snr": current["median_snr"],
        }
        return {
            "source": "current_measurement",
            "period_s": current["period_s"],
            "frequency_hz": current["frequency_hz"],
            "fresh": True,
            "measured_at_utc": current["measured_at_utc"],
        }, last_good

    previous_last_good = previous.get("last_good_measurement")
    if previous_last_good:
        return {
            "source": "last_good_measurement",
            "period_s": previous_last_good["period_s"],
            "frequency_hz": previous_last_good["frequency_hz"],
            "fresh": False,
            "measured_at_utc": previous_last_good["measured_at_utc"],
        }, previous_last_good

    baseline_frequency = 1.0 / BASELINE_PERIOD_S
    return {
        "source": "baseline",
        "period_s": BASELINE_PERIOD_S,
        "frequency_hz": baseline_frequency,
        "fresh": False,
        "measured_at_utc": None,
    }, None


def build_payload(
    result: Microseism26sResult,
    hours: float,
    snr_threshold: float,
    previous: dict[str, Any],
    history_limit: int,
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc)
    current = _current_measurement(result, hours, snr_threshold)
    app_pulse, last_good = _select_app_pulse(current, previous)

    previous_history = previous.get("history") or []
    history = [*previous_history, _history_record(current)][-history_limit:]

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": generated_at.isoformat(),
        "expires_at_utc": (generated_at + timedelta(hours=12)).isoformat(),
        "app_pulse": app_pulse,
        "breathing_rhythm": {
            "mode": "fixed_13_13",
            "period_s": BREATHING_INHALE_S + BREATHING_EXHALE_S,
            "inhale_s": BREATHING_INHALE_S,
            "exhale_s": BREATHING_EXHALE_S,
            "locked": True,
        },
        "current_measurement": current,
        "last_good_measurement": last_good,
        "history": history,
    }


def write_payload(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=DEFAULT_HOURS)
    parser.add_argument("--snr", type=float, default=DEFAULT_DETECT_SNR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--seed-journal", type=Path, default=DEFAULT_SEED_JOURNAL)
    parser.add_argument("--history-limit", type=int, default=DEFAULT_HISTORY_LIMIT)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.hours <= 0:
        print("ERROR: --hours must be positive")
        return 2
    if args.snr <= 0:
        print("ERROR: --snr must be positive")
        return 2
    if args.history_limit <= 0:
        print("ERROR: --history-limit must be positive")
        return 2

    previous = _load_previous(args.output)
    previous = _seed_previous_from_journal(
        previous,
        _load_seed_journal(args.seed_journal),
        args.history_limit,
    )
    result = detect_26s_microseism(
        hours=args.hours,
        detect_snr=args.snr,
        verbose=args.verbose,
    )
    payload = build_payload(result, args.hours, args.snr, previous, args.history_limit)
    write_payload(args.output, payload)

    current = payload["current_measurement"]
    app_pulse = payload["app_pulse"]
    print()
    print(f"Wrote {args.output}")
    print(f"  current_quality: {current['quality_status']}")
    print(f"  current_period:  {current['period_s']}")
    print(f"  current_stations:{current['stations_detected']}/{current['stations_attempted']}")
    print(f"  app_source:      {app_pulse['source']}")
    print(f"  app_period:      {app_pulse['period_s']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
