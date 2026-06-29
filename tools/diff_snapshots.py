#!/usr/bin/env python3
"""Compare two system inventory snapshots."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

# Allow ``python tools/diff_snapshots.py`` as well as
# ``python -m tools.diff_snapshots``.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).parent.parent))


LOAD_AVERAGE_SLOTS = ("1m", "5m", "15m")


def load_snapshot(path: Path) -> dict[str, Any]:
    """Read a snapshot JSON file and require a JSON object at its root."""
    path = Path(path)
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise FileNotFoundError(f"snapshot file not found: {path}") from None
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid JSON in {path}: {error.msg}") from error

    if not isinstance(snapshot, dict):
        raise ValueError(f"invalid snapshot in {path}: expected a JSON object")
    return snapshot


def _checks_by_name(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index snapshot checks by name."""
    checks = snapshot.get("checks", [])
    if not isinstance(checks, list):
        raise ValueError("invalid snapshot: checks must be a list")

    indexed: dict[str, dict[str, Any]] = {}
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get("name"), str):
            raise ValueError("invalid snapshot: each check must have a name")
        indexed[check["name"]] = check
    return indexed


def _numeric_value(snapshot: dict[str, Any], field: str) -> int | float:
    """Return a numeric snapshot field."""
    value = snapshot.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"invalid snapshot: {field} must be numeric")
    return value


def _load_average(snapshot: dict[str, Any]) -> list[int | float]:
    """Return and validate the three load average slots."""
    values = snapshot.get("load_average")
    if not isinstance(values, list) or len(values) != len(LOAD_AVERAGE_SLOTS):
        raise ValueError("invalid snapshot: load_average must contain three values")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        for value in values
    ):
        raise ValueError("invalid snapshot: load_average values must be numeric")
    return values


def compare_snapshots(
    snapshot_a: dict[str, Any], snapshot_b: dict[str, Any]
) -> dict[str, Any]:
    """Return a structured comparison of two snapshots."""
    hostname_a = snapshot_a.get("hostname")
    hostname_b = snapshot_b.get("hostname")
    uptime_a = _numeric_value(snapshot_a, "uptime_seconds")
    uptime_b = _numeric_value(snapshot_b, "uptime_seconds")
    load_a = _load_average(snapshot_a)
    load_b = _load_average(snapshot_b)
    network_a = _numeric_value(snapshot_a, "network_interfaces")
    network_b = _numeric_value(snapshot_b, "network_interfaces")

    checks_a = _checks_by_name(snapshot_a)
    checks_b = _checks_by_name(snapshot_b)
    changed_checks = []
    for name in sorted(checks_a.keys() & checks_b.keys()):
        passed_a = bool(checks_a[name].get("passed", False))
        passed_b = bool(checks_b[name].get("passed", False))
        if passed_a != passed_b:
            changed_checks.append(
                {"name": name, "before": passed_a, "after": passed_b}
            )

    new_checks = [
        {
            "name": name,
            "passed": bool(checks_b[name].get("passed", False)),
            "detail": checks_b[name].get("detail", ""),
        }
        for name in sorted(checks_b.keys() - checks_a.keys())
    ]
    removed_checks = [
        {
            "name": name,
            "passed": bool(checks_a[name].get("passed", False)),
            "detail": checks_a[name].get("detail", ""),
        }
        for name in sorted(checks_a.keys() - checks_b.keys())
    ]

    hostname_changed = hostname_a != hostname_b
    uptime_delta = uptime_b - uptime_a
    load_delta = [after - before for before, after in zip(load_a, load_b)]
    network_delta = network_b - network_a
    identical = not any(
        (
            hostname_changed,
            uptime_delta != 0,
            any(delta != 0 for delta in load_delta),
            network_delta != 0,
            changed_checks,
            new_checks,
            removed_checks,
        )
    )

    return {
        "identical": identical,
        "hostname": {
            "before": hostname_a,
            "after": hostname_b,
            "changed": hostname_changed,
        },
        "uptime_seconds": {
            "before": uptime_a,
            "after": uptime_b,
            "delta": uptime_delta,
        },
        "load_average": {
            "slots": list(LOAD_AVERAGE_SLOTS),
            "before": load_a,
            "after": load_b,
            "delta": load_delta,
        },
        "network_interfaces": {
            "before": network_a,
            "after": network_b,
            "delta": network_delta,
        },
        "checks": {
            "changed": changed_checks,
            "new": new_checks,
            "removed": removed_checks,
        },
    }


def _signed(value: int | float) -> str:
    """Format a numeric delta with an explicit sign."""
    return f"{value:+g}"


def format_text(diff: dict[str, Any]) -> str:
    """Build a human-readable snapshot diff report."""
    lines = ["=== Pulse of Earth — Snapshot Diff ===", ""]
    if diff["identical"]:
        lines.append("No differences found.")
        return "\n".join(lines)

    lines.append("[Hostname]")
    hostname = diff["hostname"]
    if hostname["changed"]:
        lines.append(f"  {hostname['before']} -> {hostname['after']}")
    else:
        lines.append("  Unchanged")
    lines.append("")

    lines.append("[Uptime]")
    uptime = diff["uptime_seconds"]
    lines.append(
        f"  {uptime['before']:g}s -> {uptime['after']:g}s "
        f"(delta {_signed(uptime['delta'])}s)"
    )
    lines.append("")

    lines.append("[Load Average]")
    load = diff["load_average"]
    for slot, before, after, delta in zip(
        load["slots"], load["before"], load["after"], load["delta"]
    ):
        lines.append(
            f"  {slot}: {before:g} -> {after:g} (delta {_signed(delta)})"
        )
    lines.append("")

    lines.append("[Network Interfaces]")
    network = diff["network_interfaces"]
    lines.append(
        f"  {network['before']:g} -> {network['after']:g} "
        f"(delta {_signed(network['delta'])})"
    )
    lines.append("")

    lines.append("[Checks]")
    checks = diff["checks"]
    if not any(checks.values()):
        lines.append("  No status changes.")
    for check in checks["changed"]:
        before = "PASS" if check["before"] else "FAIL"
        after = "PASS" if check["after"] else "FAIL"
        lines.append(f"  Changed: {check['name']}: {before} -> {after}")
    for check in checks["new"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"  New: {check['name']}: {status}")
    for check in checks["removed"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"  Removed: {check['name']}: {status}")

    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse snapshot diff command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Compare two Pulse of Earth system snapshots."
    )
    parser.add_argument("path_a", type=Path, help="earlier snapshot JSON file")
    parser.add_argument("path_b", type=Path, help="later snapshot JSON file")
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Compare two snapshots and return the documented exit code."""
    args = parse_args(argv)
    try:
        snapshot_a = load_snapshot(args.path_a)
        snapshot_b = load_snapshot(args.path_b)
        diff = compare_snapshots(snapshot_a, snapshot_b)
    except (OSError, ValueError) as error:
        print(f"diff_snapshots: {error}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(diff, indent=2, sort_keys=True))
    else:
        print(format_text(diff))
    return 0 if diff["identical"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
