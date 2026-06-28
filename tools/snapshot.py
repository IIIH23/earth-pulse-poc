#!/usr/bin/env python3
"""Capture timestamped system inventory snapshots for trend analysis."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow ``python tools/snapshot.py`` as well as ``python -m tools.snapshot``.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from tools import healthcheck
except ImportError:  # Reported as a collection failure by collect_snapshot().
    healthcheck = None  # type: ignore[assignment]


DEFAULT_OUTPUT_DIR = Path("snapshots")
DEFAULT_KEEP = 30
SNAPSHOT_PATTERN = "snapshot_*.json"


def _read_uptime() -> float:
    """Return system uptime in seconds, or zero when it is unavailable."""
    try:
        value = Path("/proc/uptime").read_text(encoding="utf-8").split()[0]
        return float(value)
    except (IndexError, OSError, ValueError):
        return 0.0


def _load_average() -> list[float]:
    """Return the one, five, and fifteen minute load averages."""
    try:
        return list(os.getloadavg())
    except (AttributeError, OSError):
        return [0.0, 0.0, 0.0]


def _network_interface_count() -> int:
    """Return the number of network interfaces visible to the process."""
    try:
        return len(socket.if_nameindex())
    except (AttributeError, OSError):
        return 0


def collect_snapshot() -> dict[str, Any]:
    """Gather health checks and system metadata into a JSON-ready dictionary."""
    if healthcheck is None:
        raise RuntimeError("tools.healthcheck could not be imported")

    results = healthcheck.run_checks()
    checks = [
        {"name": name, "passed": passed, "detail": detail}
        for name, passed, detail in results
    ]
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "hostname": socket.gethostname(),
        "uptime_seconds": _read_uptime(),
        "load_average": _load_average(),
        "network_interfaces": _network_interface_count(),
        "checks": checks,
    }


def _snapshot_datetime(snapshot: dict[str, Any]) -> datetime:
    """Extract the snapshot timestamp, falling back to the current UTC time."""
    timestamp = snapshot.get("timestamp")
    if isinstance(timestamp, str):
        try:
            parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc)


def save_snapshot(
    snapshot: dict[str, Any],
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    keep: int = DEFAULT_KEEP,
    verbose: bool = False,
) -> Path:
    """Write a snapshot as JSON and retain only the newest ``keep`` files."""
    if keep < 1:
        raise ValueError("keep must be at least 1")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = _snapshot_datetime(snapshot).strftime("%Y-%m-%d_%H%M%S")
    output_path = output_dir / f"snapshot_{timestamp}.json"
    output_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # The timestamp format sorts chronologically, independent of copied-file mtimes.
    snapshots = sorted(output_dir.glob(SNAPSHOT_PATTERN), reverse=True)
    for old_snapshot in snapshots[keep:]:
        old_snapshot.unlink()
        if verbose:
            print(f"Pruned {old_snapshot}")

    if verbose:
        print(f"Saved {output_path}")
    return output_path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse snapshot command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Capture a timestamped Pulse of Earth system snapshot."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="snapshot storage directory (default: ./snapshots/)",
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=DEFAULT_KEEP,
        metavar="N",
        help="number of most recent snapshots to retain (default: 30)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the snapshot without writing it",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print snapshot and pruning details",
    )
    args = parser.parse_args(argv)
    if args.keep < 1:
        parser.error("--keep must be at least 1")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    """Collect and optionally save a snapshot, returning a documented exit code."""
    args = parse_args(argv)
    try:
        snapshot = collect_snapshot()
    except Exception as error:
        print(f"snapshot: collection failed: {error}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(json.dumps(snapshot, indent=2, sort_keys=True))
        return 0

    try:
        output_path = save_snapshot(
            snapshot,
            output_dir=args.output_dir,
            keep=args.keep,
            verbose=args.verbose,
        )
    except (OSError, TypeError, ValueError) as error:
        print(f"snapshot: write failed: {error}", file=sys.stderr)
        return 2

    if not args.verbose:
        print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
