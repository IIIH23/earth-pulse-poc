#!/usr/bin/env python3
"""Run one 26-second microseism collection cycle and append a JSONL record."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from statistics import mean
from typing import Any

import numpy as np

from earth_26s_detector import (
    DEFAULT_DETECT_SNR,
    DEFAULT_HOURS,
    Microseism26sResult,
    detect_26s_microseism,
)


DEFAULT_JOURNAL = Path("earth_26s_runs.jsonl")


def _finite(value: float | None) -> float | None:
    if value is None or np.isnan(value):
        return None
    return float(value)


def _snr_values(record: dict[str, Any]) -> list[float]:
    return [
        float(station["snr"])
        for station in record.get("per_station", [])
        if station.get("snr") is not None
    ]


def result_to_record(
    result: Microseism26sResult,
    hours: float,
    snr_threshold: float,
) -> dict[str, Any]:
    snrs = [detection.snr for detection in result.per_station if detection.snr is not None]
    best_detection = max(
        (detection for detection in result.per_station if detection.snr is not None),
        key=lambda detection: detection.snr or 0,
        default=None,
    )

    return {
        "timestamp_utc": result.timestamp_utc.isoformat(),
        "collection_hours": hours,
        "snr_threshold": snr_threshold,
        "detected_any": result.detected_any,
        "consensus_period_s": _finite(result.consensus_period_s),
        "consensus_frequency_hz": _finite(result.consensus_frequency_hz),
        "confidence_label": result.confidence_label,
        "stations_detected": result.stations_detected,
        "stations_attempted": result.stations_attempted,
        "station_errors": sum(1 for detection in result.per_station if detection.error),
        "best_station": best_detection.code if best_detection else None,
        "best_snr": _finite(best_detection.snr) if best_detection else None,
        "median_snr": float(np.median(snrs)) if snrs else None,
        "per_station": [asdict(detection) for detection in result.per_station],
    }


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def append_record(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def print_comparison(record: dict[str, Any], previous: dict[str, Any] | None) -> None:
    print()
    print("Journal entry")
    print(f"  timestamp_utc:       {record['timestamp_utc']}")
    print(f"  detected_any:        {record['detected_any']}")
    print(f"  consensus_period_s:  {record['consensus_period_s']}")
    print(f"  consensus_freq_hz:   {record['consensus_frequency_hz']}")
    print(f"  confidence:          {record['confidence_label']}")
    print(f"  stations_detected:   {record['stations_detected']}/{record['stations_attempted']}")
    print(f"  station_errors:      {record['station_errors']}")
    print(f"  best_station_snr:    {record['best_station']} / {record['best_snr']}")
    print(f"  median_snr:          {record['median_snr']}")

    if not previous:
        print("  comparison:          first recorded 26s run")
        return

    print("  comparison:")
    print(f"    previous_time:     {previous.get('timestamp_utc')}")
    print(f"    detected_change:   {previous.get('detected_any')} -> {record['detected_any']}")
    print(
        "    station_delta:     "
        f"{record['stations_detected'] - int(previous.get('stations_detected') or 0):+d}"
    )

    previous_period = previous.get("consensus_period_s")
    current_period = record.get("consensus_period_s")
    if previous_period is not None and current_period is not None:
        print(f"    period_delta_s:    {current_period - previous_period:+.2f}")
    else:
        print("    period_delta_s:    unavailable")

    previous_snr = previous.get("best_snr")
    current_snr = record.get("best_snr")
    if previous_snr is not None and current_snr is not None:
        print(f"    best_snr_delta:    {current_snr - previous_snr:+.1f}")
    else:
        print("    best_snr_delta:    unavailable")


def print_quality_assessment(records: list[dict[str, Any]]) -> None:
    if not records:
        return

    attempted = sum(int(record.get("stations_attempted") or 0) for record in records)
    errors = sum(int(record.get("station_errors") or 0) for record in records)
    detected_runs = [record for record in records if record.get("detected_any")]
    periods = [
        float(record["consensus_period_s"])
        for record in detected_runs
        if record.get("consensus_period_s") is not None
    ]
    best_snrs = [
        float(record["best_snr"])
        for record in records
        if record.get("best_snr") is not None
    ]

    data_success_rate = 1.0 - (errors / attempted) if attempted else 0.0
    detection_rate = len(detected_runs) / len(records)

    print()
    print("Script quality assessment")
    print(f"  runs_recorded:       {len(records)}")
    print(f"  data_success_rate:   {data_success_rate:.2%}")
    print(f"  detection_rate:      {detection_rate:.2%}")
    if periods:
        print(f"  detected_period_avg: {mean(periods):.2f} s")
        print(f"  detected_period_rng: {max(periods) - min(periods):.2f} s")
    else:
        print("  detected_period_avg: unavailable")
        print("  detected_period_rng: unavailable")
    if best_snrs:
        print(f"  best_snr_avg:        {mean(best_snrs):.1f}")
    else:
        print("  best_snr_avg:        unavailable")

    if data_success_rate < 0.7:
        print("  verdict:             data access is weak; station/location fallback is needed")
    elif len(records) < 3:
        print("  verdict:             too early to judge; collect at least 3 hourly runs")
    elif detection_rate == 0:
        print("  verdict:             no 26s detections yet; try longer windows or lower SNR review")
    elif periods and max(periods) - min(periods) <= 1.5:
        print("  verdict:             detections are coherent; script is behaving plausibly")
    else:
        print("  verdict:             detections need review; period spread or SNR may be unstable")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=DEFAULT_HOURS)
    parser.add_argument("--snr", type=float, default=DEFAULT_DETECT_SNR)
    parser.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    if args.hours <= 0:
        print("ERROR: --hours must be positive")
        return 2
    if args.snr <= 0:
        print("ERROR: --snr must be positive")
        return 2

    previous_records = load_records(args.journal)
    result = detect_26s_microseism(
        hours=args.hours,
        detect_snr=args.snr,
        verbose=args.verbose,
    )
    record = result_to_record(result, args.hours, args.snr)
    append_record(args.journal, record)

    records = [*previous_records, record]
    print_comparison(record, previous_records[-1] if previous_records else None)
    print_quality_assessment(records)

    # No detection is a valid scientific observation, not a process failure.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
