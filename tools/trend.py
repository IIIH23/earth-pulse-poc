#!/usr/bin/env python3
"""Analyze trends across timestamped system inventory snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

# Allow ``python tools/trend.py`` as well as ``python -m tools.trend``.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).parent.parent))

SNAPSHOT_PATTERN = "snapshot_*.json"


def load_snapshots(snapshot_dir: Path) -> list[dict[str, Any]]:
    """Read and parse all snapshot JSON files from a directory.

    Returns snapshots sorted by timestamp ascending. Malformed JSON files
    are silently skipped.
    """
    snapshot_dir = Path(snapshot_dir)
    if not snapshot_dir.exists():
        raise FileNotFoundError(f"snapshot directory not found: {snapshot_dir}")

    snapshots: list[dict[str, Any]] = []
    for path in sorted(snapshot_dir.glob(SNAPSHOT_PATTERN)):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            snapshots.append(data)
        except (json.JSONDecodeError, OSError):
            continue

    snapshots.sort(key=lambda s: s.get("timestamp", ""))
    return snapshots


def _stats(values: list[float]) -> dict[str, float | None]:
    """Compute min, max, mean over a list of numbers."""
    if not values:
        return {"min": None, "max": None, "mean": None, "latest": None}
    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
        "latest": values[-1],
    }


def analyze_trends(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute trend statistics over a collection of snapshots."""
    if not snapshots:
        return {
            "period": {"first": None, "last": None, "count": 0},
            "uptime": {"min": None, "max": None, "latest": None},
            "load_average_1m": {"min": None, "max": None, "mean": None, "latest": None},
            "load_average_5m": {"min": None, "max": None, "mean": None, "latest": None},
            "load_average_15m": {"min": None, "max": None, "mean": None, "latest": None},
            "network_interfaces": {"min": None, "max": None, "latest": None},
            "health": {
                "total_checks": 0,
                "passed_checks": 0,
                "failed_checks": 0,
                "pass_rate": 0.0,
            },
            "check_details": {},
        }

    timestamps = [s.get("timestamp", "") for s in snapshots]
    uptimes = [float(s.get("uptime_seconds", 0)) for s in snapshots]
    net_ifs = [int(s.get("network_interfaces", 0)) for s in snapshots]

    load_1m = [float(s.get("load_average", [0, 0, 0])[0]) for s in snapshots]
    load_5m = [float(s.get("load_average", [0, 0, 0])[1]) for s in snapshots]
    load_15m = [float(s.get("load_average", [0, 0, 0])[2]) for s in snapshots]

    # Health aggregation
    check_totals: dict[str, dict[str, int]] = {}
    total_checks = 0
    passed_checks = 0

    for snap in snapshots:
        for check in snap.get("checks", []):
            name = check.get("name", "unknown")
            passed = check.get("passed", False)
            if name not in check_totals:
                check_totals[name] = {"passed": 0, "total": 0}
            check_totals[name]["total"] += 1
            total_checks += 1
            if passed:
                check_totals[name]["passed"] += 1
                passed_checks += 1

    check_details = {}
    for name, counts in check_totals.items():
        rate = counts["passed"] / counts["total"] if counts["total"] > 0 else 0.0
        check_details[name] = {
            "passed": counts["passed"],
            "total": counts["total"],
            "pass_rate": rate,
        }

    pass_rate = passed_checks / total_checks if total_checks > 0 else 0.0

    return {
        "period": {
            "first": timestamps[0],
            "last": timestamps[-1],
            "count": len(snapshots),
        },
        "uptime": _stats(uptimes),
        "load_average_1m": _stats(load_1m),
        "load_average_5m": _stats(load_5m),
        "load_average_15m": _stats(load_15m),
        "network_interfaces": _stats([float(v) for v in net_ifs]),
        "health": {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": total_checks - passed_checks,
            "pass_rate": pass_rate,
        },
        "check_details": check_details,
    }


def _format_uptime(seconds: float | None) -> str:
    """Format uptime in human-readable form (days/hours/minutes)."""
    if seconds is None:
        return "N/A"
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m")
    return " ".join(parts) if parts else "0m"


def _format_stat(stat: dict[str, float | None]) -> str:
    """Format a stats dict (min/max/mean/latest) as a compact string."""
    if stat["latest"] is None:
        return "N/A"
    return (
        f"latest={stat['latest']:.2f} min={stat['min']:.2f} "
        f"max={stat['max']:.2f} mean={stat['mean']:.2f}"
    )


def _health_emoji(pass_rate: float) -> str:
    """Return status emoji based on pass rate."""
    if pass_rate >= 0.95:
        return "OK"
    if pass_rate >= 0.8:
        return "WARN"
    return "CRIT"


def format_report(analysis: dict[str, Any], verbose: bool = False) -> str:
    """Build a human-readable trend report from analysis results."""
    lines: list[str] = []
    period = analysis["period"]

    lines.append("=== Pulse of Earth — Snapshot Trend Report ===")
    lines.append("")

    # Period
    lines.append("[Period]")
    if period["count"] == 0:
        lines.append("  No snapshots found.")
        return "\n".join(lines)
    lines.append(f"  First: {period['first']}")
    lines.append(f"  Last:  {period['last']}")
    lines.append(f"  Count: {period['count']}")
    lines.append("")

    # Uptime
    lines.append("[Uptime]")
    uptime = analysis["uptime"]
    if uptime["latest"] is not None:
        lines.append(f"  Latest: {_format_uptime(uptime['latest'])}")
        lines.append(f"  Min:    {_format_uptime(uptime['min'])}")
        lines.append(f"  Max:    {_format_uptime(uptime['max'])}")
    else:
        lines.append("  N/A")
    lines.append("")

    # Load Average
    lines.append("[Load Average]")
    lines.append(f"  1m:  {_format_stat(analysis['load_average_1m'])}")
    lines.append(f"  5m:  {_format_stat(analysis['load_average_5m'])}")
    lines.append(f"  15m: {_format_stat(analysis['load_average_15m'])}")
    lines.append("")

    # Network Interfaces
    lines.append("[Network Interfaces]")
    net = analysis["network_interfaces"]
    if net["latest"] is not None:
        lines.append(
            f"  Latest: {int(net['latest'])}  Min: {int(net['min'])}  Max: {int(net['max'])}"
        )
    else:
        lines.append("  N/A")
    lines.append("")

    # Health
    lines.append("[Health]")
    health = analysis["health"]
    if health["total_checks"] == 0:
        lines.append("  No check data available.")
    else:
        pass_rate = health["pass_rate"]
        emoji = _health_emoji(pass_rate)
        lines.append(
            f"  Overall: {emoji} {pass_rate:.1%} "
            f"({health['passed_checks']}/{health['total_checks']} checks passed)"
        )
        if verbose and analysis["check_details"]:
            lines.append("  Per-check:")
            for name, detail in analysis["check_details"].items():
                check_emoji = _health_emoji(detail["pass_rate"])
                lines.append(
                    f"    {check_emoji} {name}: {detail['pass_rate']:.1%} "
                    f"({detail['passed']}/{detail['total']})"
                )
    lines.append("")

    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse trend command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze trends across Pulse of Earth system snapshots."
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=Path("snapshots"),
        help="directory containing snapshot JSON files (default: ./snapshots/)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="output raw JSON instead of text report",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="include per-check details in report",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run trend analysis and print report, returning a documented exit code."""
    args = parse_args(argv)

    try:
        snapshots = load_snapshots(args.snapshot_dir)
    except FileNotFoundError as error:
        print(f"trend: {error}", file=sys.stderr)
        return 2

    if not snapshots:
        print("trend: no snapshots found", file=sys.stderr)
        return 1

    analysis = analyze_trends(snapshots)

    if args.json:
        print(json.dumps(analysis, indent=2, sort_keys=True))
    else:
        print(format_report(analysis, verbose=args.verbose))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
