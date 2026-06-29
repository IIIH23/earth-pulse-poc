"""Tests for trend analysis over system snapshots."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import trend


def sample_snapshot(
    timestamp: str = "2026-06-29T12:00:00+00:00",
    *,
    uptime: float = 86400.0,
    load: list[float] | None = None,
    net_ifs: int = 2,
    checks: list[dict] | None = None,
) -> dict:
    return {
        "timestamp": timestamp,
        "hostname": "test-node",
        "uptime_seconds": uptime,
        "load_average": load or [0.1, 0.2, 0.15],
        "network_interfaces": net_ifs,
        "checks": checks or [
            {"name": "disk usage < 80%", "passed": True, "detail": "42% used"},
        ],
    }


# --- load_snapshots ---


def test_load_snapshots_returns_sorted_by_timestamp(tmp_path: Path):
    for ts in ["2026-06-29T14:00:00+00:00", "2026-06-29T10:00:00+00:00"]:
        snap = sample_snapshot(ts)
        path = tmp_path / f"snapshot_{ts.replace(':', '').replace('+00:00', '')}.json"
        path.write_text(json.dumps(snap), encoding="utf-8")

    results = trend.load_snapshots(tmp_path)
    assert len(results) == 2
    assert results[0]["timestamp"] == "2026-06-29T10:00:00+00:00"
    assert results[1]["timestamp"] == "2026-06-29T14:00:00+00:00"


def test_load_snapshots_raises_when_dir_missing():
    with pytest.raises(FileNotFoundError):
        trend.load_snapshots(Path("/nonexistent/dir"))


def test_load_snapshots_skips_malformed_json(tmp_path: Path):
    good = sample_snapshot("2026-06-29T12:00:00+00:00")
    (tmp_path / "snapshot_2026-06-29_120000.json").write_text(
        json.dumps(good), encoding="utf-8"
    )
    (tmp_path / "snapshot_2026-06-29_130000.json").write_text(
        "not json{", encoding="utf-8"
    )

    results = trend.load_snapshots(tmp_path)
    assert len(results) == 1
    assert results[0]["timestamp"] == "2026-06-29T12:00:00+00:00"


def test_load_snapshots_empty_dir(tmp_path: Path):
    results = trend.load_snapshots(tmp_path)
    assert results == []


# --- analyze_trends ---


def test_analyze_trends_empty_list():
    result = trend.analyze_trends([])
    assert result["period"]["count"] == 0
    assert result["period"]["first"] is None
    assert result["uptime"]["latest"] is None
    assert result["health"]["total_checks"] == 0


def test_analyze_trends_computes_stats():
    snaps = [
        sample_snapshot("2026-06-29T10:00:00+00:00", uptime=100.0, load=[0.1, 0.2, 0.3]),
        sample_snapshot("2026-06-29T11:00:00+00:00", uptime=200.0, load=[0.5, 0.4, 0.3]),
        sample_snapshot("2026-06-29T12:00:00+00:00", uptime=150.0, load=[0.2, 0.3, 0.4]),
    ]
    result = trend.analyze_trends(snaps)

    assert result["period"]["count"] == 3
    assert result["period"]["first"] == "2026-06-29T10:00:00+00:00"
    assert result["period"]["last"] == "2026-06-29T12:00:00+00:00"

    assert result["uptime"]["min"] == 100.0
    assert result["uptime"]["max"] == 200.0
    assert result["uptime"]["latest"] == 150.0

    assert result["load_average_1m"]["min"] == 0.1
    assert result["load_average_1m"]["max"] == 0.5
    assert result["load_average_1m"]["latest"] == 0.2
    assert result["load_average_1m"]["mean"] == pytest.approx(0.266666, rel=1e-3)


def test_analyze_trends_health_aggregation():
    snaps = [
        sample_snapshot(
            "2026-06-29T10:00:00+00:00",
            checks=[
                {"name": "disk", "passed": True, "detail": "ok"},
                {"name": "memory", "passed": False, "detail": "high"},
            ],
        ),
        sample_snapshot(
            "2026-06-29T11:00:00+00:00",
            checks=[
                {"name": "disk", "passed": True, "detail": "ok"},
                {"name": "memory", "passed": True, "detail": "ok"},
            ],
        ),
    ]
    result = trend.analyze_trends(snaps)

    assert result["health"]["total_checks"] == 4
    assert result["health"]["passed_checks"] == 3
    assert result["health"]["failed_checks"] == 1
    assert result["health"]["pass_rate"] == 0.75

    assert result["check_details"]["disk"]["pass_rate"] == 1.0
    assert result["check_details"]["disk"]["passed"] == 2
    assert result["check_details"]["memory"]["pass_rate"] == 0.5
    assert result["check_details"]["memory"]["passed"] == 1


# --- format_report ---


def test_format_report_empty():
    analysis = trend.analyze_trends([])
    report = trend.format_report(analysis)
    assert "No snapshots found" in report


def test_format_report_contains_sections():
    snaps = [
        sample_snapshot("2026-06-29T10:00:00+00:00"),
        sample_snapshot("2026-06-29T11:00:00+00:00"),
    ]
    analysis = trend.analyze_trends(snaps)
    report = trend.format_report(analysis, verbose=True)

    assert "[Period]" in report
    assert "[Uptime]" in report
    assert "[Load Average]" in report
    assert "[Network Interfaces]" in report
    assert "[Health]" in report
    assert "Count: 2" in report


def test_format_report_verbose_shows_per_check():
    snaps = [
        sample_snapshot(
            "2026-06-29T10:00:00+00:00",
            checks=[{"name": "disk", "passed": True, "detail": "ok"}],
        ),
    ]
    analysis = trend.analyze_trends(snaps)
    report = trend.format_report(analysis, verbose=True)
    assert "Per-check:" in report
    assert "disk" in report


# --- CLI ---


def test_main_text_report(tmp_path: Path, capsys):
    snap = sample_snapshot("2026-06-29T12:00:00+00:00")
    (tmp_path / "snapshot_2026-06-29_120000.json").write_text(
        json.dumps(snap), encoding="utf-8"
    )

    exit_code = trend.main(["--snapshot-dir", str(tmp_path)])
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Trend Report" in output


def test_main_json_output(tmp_path: Path, capsys):
    snap = sample_snapshot("2026-06-29T12:00:00+00:00")
    (tmp_path / "snapshot_2026-06-29_120000.json").write_text(
        json.dumps(snap), encoding="utf-8"
    )

    exit_code = trend.main(["--snapshot-dir", str(tmp_path), "--json"])
    assert exit_code == 0
    output = capsys.readouterr().out
    parsed = json.loads(output)
    assert parsed["period"]["count"] == 1


def test_main_no_snapshots(tmp_path: Path, capsys):
    exit_code = trend.main(["--snapshot-dir", str(tmp_path)])
    assert exit_code == 1
    assert "no snapshots found" in capsys.readouterr().err


def test_main_dir_not_found(capsys):
    exit_code = trend.main(["--snapshot-dir", "/nonexistent/path"])
    assert exit_code == 2
    assert "not found" in capsys.readouterr().err


def test_parse_args_defaults():
    args = trend.parse_args([])
    assert args.snapshot_dir == Path("snapshots")
    assert args.json is False
    assert args.verbose is False
