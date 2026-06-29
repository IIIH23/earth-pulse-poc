"""Tests for comparing system inventory snapshots."""

from __future__ import annotations

import json
from pathlib import Path

from tools import diff_snapshots


def sample_snapshot() -> dict:
    return {
        "timestamp": "2026-06-29T12:00:00+00:00",
        "hostname": "earth-node",
        "uptime_seconds": 100.0,
        "load_average": [0.1, 0.2, 0.3],
        "network_interfaces": 2,
        "checks": [
            {"name": "disk", "passed": True, "detail": "42% used"},
            {"name": "memory", "passed": True, "detail": "healthy"},
        ],
    }


def write_snapshot(path: Path, snapshot: dict) -> None:
    path.write_text(json.dumps(snapshot), encoding="utf-8")


def test_identical_snapshots_return_zero(tmp_path: Path, capsys):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_snapshot(first, sample_snapshot())
    write_snapshot(second, sample_snapshot())

    assert diff_snapshots.main([str(first), str(second)]) == 0
    assert "No differences found." in capsys.readouterr().out


def test_different_hostnames_are_reported():
    first = sample_snapshot()
    second = sample_snapshot()
    second["hostname"] = "mars-node"

    result = diff_snapshots.compare_snapshots(first, second)

    assert result["identical"] is False
    assert result["hostname"] == {
        "before": "earth-node",
        "after": "mars-node",
        "changed": True,
    }


def test_changed_check_status_is_reported():
    first = sample_snapshot()
    second = sample_snapshot()
    second["checks"][0]["passed"] = False

    result = diff_snapshots.compare_snapshots(first, second)

    assert result["checks"]["changed"] == [
        {"name": "disk", "before": True, "after": False}
    ]


def test_new_and_removed_checks_are_reported():
    first = sample_snapshot()
    second = sample_snapshot()
    second["checks"] = [
        second["checks"][0],
        {"name": "network", "passed": False, "detail": "offline"},
    ]

    result = diff_snapshots.compare_snapshots(first, second)

    assert [check["name"] for check in result["checks"]["new"]] == ["network"]
    assert [check["name"] for check in result["checks"]["removed"]] == ["memory"]


def test_load_average_delta_is_reported():
    first = sample_snapshot()
    second = sample_snapshot()
    second["load_average"] = [0.4, 0.1, 0.5]

    result = diff_snapshots.compare_snapshots(first, second)

    assert result["load_average"]["delta"] == [
        0.30000000000000004,
        -0.1,
        0.2,
    ]


def test_uptime_and_network_deltas_are_reported():
    first = sample_snapshot()
    second = sample_snapshot()
    second["uptime_seconds"] = 125.0
    second["network_interfaces"] = 4

    result = diff_snapshots.compare_snapshots(first, second)

    assert result["uptime_seconds"]["delta"] == 25.0
    assert result["network_interfaces"]["delta"] == 2


def test_file_not_found_returns_two(tmp_path: Path, capsys):
    missing = tmp_path / "missing.json"

    assert diff_snapshots.main([str(missing), str(missing)]) == 2
    assert "not found" in capsys.readouterr().err


def test_invalid_json_returns_two(tmp_path: Path, capsys):
    invalid = tmp_path / "invalid.json"
    valid = tmp_path / "valid.json"
    invalid.write_text("not JSON{", encoding="utf-8")
    write_snapshot(valid, sample_snapshot())

    assert diff_snapshots.main([str(invalid), str(valid)]) == 2
    assert "invalid JSON" in capsys.readouterr().err


def test_json_format_outputs_structured_diff(tmp_path: Path, capsys):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    before = sample_snapshot()
    after = sample_snapshot()
    after["hostname"] = "ocean-node"
    write_snapshot(first, before)
    write_snapshot(second, after)

    exit_code = diff_snapshots.main(
        [str(first), str(second), "--format", "json"]
    )
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["identical"] is False
    assert output["hostname"]["after"] == "ocean-node"


def test_text_format_has_clear_section_headers(tmp_path: Path, capsys):
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    before = sample_snapshot()
    after = sample_snapshot()
    after["uptime_seconds"] = 101.0
    write_snapshot(first, before)
    write_snapshot(second, after)

    assert diff_snapshots.main([str(first), str(second)]) == 1
    output = capsys.readouterr().out
    assert "[Hostname]" in output
    assert "[Uptime]" in output
    assert "[Load Average]" in output
    assert "[Network Interfaces]" in output
    assert "[Checks]" in output
