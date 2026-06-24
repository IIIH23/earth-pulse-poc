#!/usr/bin/env python3
"""Run one Earth Pulse collection cycle and append a JSONL observation."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from earth_period import compute_earth_rhythm


DEFAULT_JOURNAL = Path("earth_period_runs.jsonl")


def _finite(value: float) -> float | None:
    if value is None or np.isnan(value):
        return None
    return float(value)


def rhythm_to_record(rhythm: Any, hours: float) -> dict[str, Any]:
    return {
        "timestamp_utc": rhythm.timestamp_utc.isoformat(),
        "collection_hours": hours,
        "period_s": _finite(rhythm.period_s),
        "frequency_hz": _finite(rhythm.frequency_hz),
        "confidence": float(rhythm.confidence),
        "confidence_label": rhythm.confidence_label,
        "stations_used": rhythm.stations_used,
        "stations_attempted": rhythm.stations_attempted,
        "per_station": [asdict(result) for result in rhythm.per_station],
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
    print(f"  timestamp_utc:      {record['timestamp_utc']}")
    print(f"  period_s:           {record['period_s']}")
    print(f"  frequency_hz:       {record['frequency_hz']}")
    print(f"  confidence:         {record['confidence']:.2f} ({record['confidence_label']})")
    print(f"  stations_used:      {record['stations_used']}/{record['stations_attempted']}")

    if not previous:
        print("  comparison:         first recorded run")
        return

    prev_period = previous.get("period_s")
    current_period = record.get("period_s")
    if prev_period is None or current_period is None:
        print("  comparison:         unavailable because one run has no period")
        return

    delta = current_period - prev_period
    print(f"  previous_period_s:  {prev_period}")
    print(f"  delta_period_s:     {delta:+.2f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hours", type=float, default=1.0)
    parser.add_argument("--journal", type=Path, default=DEFAULT_JOURNAL)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args()

    previous_records = load_records(args.journal)
    rhythm = compute_earth_rhythm(hours=args.hours, verbose=args.verbose)
    record = rhythm_to_record(rhythm, args.hours)
    append_record(args.journal, record)
    print_comparison(record, previous_records[-1] if previous_records else None)

    return 0 if record["period_s"] is not None else 1


if __name__ == "__main__":
    raise SystemExit(main())
