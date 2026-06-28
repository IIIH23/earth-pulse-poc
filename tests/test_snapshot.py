"""Tests for timestamped system inventory snapshots."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from tools import healthcheck
from tools import snapshot


CHECK_RESULTS: list[healthcheck.CheckResult] = [
    ("disk usage < 80%", True, "42.0% used"),
]


def sample_snapshot(timestamp: str = "2026-06-29T12:34:56+00:00") -> dict:
    return {
        "timestamp": timestamp,
        "hostname": "earth-node",
        "uptime_seconds": 123.4,
        "load_average": [0.1, 0.2, 0.3],
        "network_interfaces": 2,
        "checks": [
            {
                "name": "disk usage < 80%",
                "passed": True,
                "detail": "42.0% used",
            }
        ],
    }


def test_collect_snapshot_returns_expected_keys():
    with patch("tools.snapshot.healthcheck.run_checks", return_value=CHECK_RESULTS):
        result = snapshot.collect_snapshot()

    assert set(result) == {
        "timestamp",
        "hostname",
        "uptime_seconds",
        "load_average",
        "network_interfaces",
        "checks",
    }
    assert datetime.fromisoformat(result["timestamp"]).tzinfo == timezone.utc


def test_collect_snapshot_calls_healthcheck_run_checks():
    with patch(
        "tools.snapshot.healthcheck.run_checks", return_value=CHECK_RESULTS
    ) as run_checks:
        snapshot.collect_snapshot()

    run_checks.assert_called_once_with()


def test_save_snapshot_writes_valid_json_with_timestamped_name(tmp_path):
    payload = sample_snapshot()

    output_path = snapshot.save_snapshot(payload, tmp_path)

    assert re.fullmatch(
        r"snapshot_\d{4}-\d{2}-\d{2}_\d{6}\.json", output_path.name
    )
    assert output_path.name == "snapshot_2026-06-29_123456.json"
    assert json.loads(output_path.read_text(encoding="utf-8")) == payload


def test_save_snapshot_prunes_old_files(tmp_path):
    keep = 3
    for second in range(keep + 1):
        payload = sample_snapshot(f"2026-06-29T12:34:{second:02d}+00:00")
        snapshot.save_snapshot(payload, tmp_path, keep=keep)

    remaining = sorted(tmp_path.glob("snapshot_*.json"))
    assert len(remaining) == keep
    assert [path.name for path in remaining] == [
        "snapshot_2026-06-29_123401.json",
        "snapshot_2026-06-29_123402.json",
        "snapshot_2026-06-29_123403.json",
    ]


def test_main_dry_run_does_not_write_files(tmp_path, capsys):
    with patch("tools.snapshot.collect_snapshot", return_value=sample_snapshot()):
        exit_code = snapshot.main(["--dry-run", "--output-dir", str(tmp_path)])

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == sample_snapshot()
    assert list(tmp_path.iterdir()) == []


def test_main_returns_zero_on_success(tmp_path):
    with patch("tools.snapshot.collect_snapshot", return_value=sample_snapshot()):
        exit_code = snapshot.main(["--output-dir", str(tmp_path)])

    assert exit_code == 0
    assert len(list(tmp_path.glob("snapshot_*.json"))) == 1


def test_main_returns_one_when_collection_fails(tmp_path, capsys):
    with patch(
        "tools.snapshot.collect_snapshot", side_effect=RuntimeError("checks unavailable")
    ):
        exit_code = snapshot.main(["--output-dir", str(tmp_path)])

    assert exit_code == 1
    assert "collection failed" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


def test_main_returns_two_when_write_fails(tmp_path, capsys):
    with (
        patch("tools.snapshot.collect_snapshot", return_value=sample_snapshot()),
        patch("tools.snapshot.save_snapshot", side_effect=OSError("disk full")),
    ):
        exit_code = snapshot.main(["--output-dir", str(tmp_path)])

    assert exit_code == 2
    assert "write failed" in capsys.readouterr().err


def test_parse_args_defaults():
    args = snapshot.parse_args([])

    assert args.output_dir == Path("snapshots")
    assert args.keep == 30
    assert args.dry_run is False
    assert args.verbose is False
