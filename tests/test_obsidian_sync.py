"""Tests for the Obsidian synchronization tool."""

from __future__ import annotations

from datetime import date

import pytest

from tools import obsidian_sync


def make_repo(tmp_path):
    """Create the canonical files needed by a sync."""
    (tmp_path / "logs").mkdir()
    (tmp_path / "AUTOPILOT_STATE.md").write_text(
        "# State\n\nCurrent state.\n", encoding="utf-8"
    )
    (tmp_path / "ROADMAP.md").write_text(
        "# Roadmap\n\nNext task.\n", encoding="utf-8"
    )
    (tmp_path / "logs" / "AUTOPILOT_LOG.md").write_text(
        """# Autopilot Log

## 2026-06-28T13:30:00Z — Cycle 10

- Latest action

## 2026-06-28T07:00:00Z — Cycle 9

- Earlier action on latest day

## 2026-06-27T08:43:43Z

- Old action
""",
        encoding="utf-8",
    )


def test_extract_recent_log_entries_selects_all_sections_from_latest_date():
    text = """# Log

## 2026-06-27T23:00:00Z
old

## 2026-06-28T01:00:00Z
new one

## 2026-06-28T02:00:00Z
new two
"""

    log_date, content = obsidian_sync.extract_recent_log_entries(text)

    assert log_date == date(2026, 6, 28)
    assert content.startswith("# Autopilot Log — 2026-06-28\n")
    assert "new one" in content
    assert "new two" in content
    assert "old" not in content
    assert content.endswith("\n")


def test_extract_recent_log_entries_handles_non_chronological_sections():
    text = """## 2026-06-28 — summary
latest

## 2026-06-27T23:00:00Z
older
"""

    log_date, content = obsidian_sync.extract_recent_log_entries(text)

    assert log_date == date(2026, 6, 28)
    assert "latest" in content
    assert "older" not in content


def test_extract_recent_log_entries_rejects_log_without_dated_sections():
    with pytest.raises(ValueError, match="no dated entries"):
        obsidian_sync.extract_recent_log_entries("# Empty log\n")


def test_sync_writes_state_roadmap_and_latest_daily_log(tmp_path):
    make_repo(tmp_path)
    vault = tmp_path / "vault"

    results = obsidian_sync.sync_to_obsidian(tmp_path, vault)

    assert [(result.path.name, result.action) for result in results] == [
        ("STATE.md", "create"),
        ("ROADMAP.md", "create"),
        ("LOG-2026-06-28.md", "create"),
    ]
    assert (vault / "STATE.md").read_text(encoding="utf-8") == (
        tmp_path / "AUTOPILOT_STATE.md"
    ).read_text(encoding="utf-8")
    assert (vault / "ROADMAP.md").read_text(encoding="utf-8") == (
        tmp_path / "ROADMAP.md"
    ).read_text(encoding="utf-8")
    daily_log = (vault / "LOG-2026-06-28.md").read_text(encoding="utf-8")
    assert "Latest action" in daily_log
    assert "Earlier action on latest day" in daily_log
    assert "Old action" not in daily_log


def test_sync_overwrites_managed_files_and_leaves_other_files(tmp_path):
    make_repo(tmp_path)
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "STATE.md").write_text("human edit\n", encoding="utf-8")
    (vault / "personal-note.md").write_text("keep me\n", encoding="utf-8")

    results = obsidian_sync.sync_to_obsidian(tmp_path, vault)

    assert results[0].action == "update"
    assert (vault / "STATE.md").read_text(encoding="utf-8") == (
        "# State\n\nCurrent state.\n"
    )
    assert (vault / "personal-note.md").read_text(encoding="utf-8") == "keep me\n"


def test_sync_reports_unchanged_files_on_repeated_run(tmp_path):
    make_repo(tmp_path)
    vault = tmp_path / "vault"
    obsidian_sync.sync_to_obsidian(tmp_path, vault)

    results = obsidian_sync.sync_to_obsidian(tmp_path, vault)

    assert {result.action for result in results} == {"unchanged"}


def test_dry_run_does_not_create_destination(tmp_path):
    make_repo(tmp_path)
    vault = tmp_path / "vault"

    results = obsidian_sync.sync_to_obsidian(tmp_path, vault, dry_run=True)

    assert not vault.exists()
    assert [result.action for result in results] == ["create", "create", "create"]


def test_parse_args_accepts_flags(tmp_path):
    args = obsidian_sync.parse_args(
        ["--dry-run", "--vault-path", str(tmp_path / "custom-vault")]
    )

    assert args.dry_run is True
    assert args.vault_path == tmp_path / "custom-vault"


def test_main_uses_vault_override_and_prints_actions(tmp_path, monkeypatch, capsys):
    make_repo(tmp_path)
    vault = tmp_path / "custom-vault"
    monkeypatch.setattr(obsidian_sync, "REPO_ROOT", tmp_path)

    assert obsidian_sync.main(["--vault-path", str(vault)]) == 0
    assert (vault / "STATE.md").is_file()
    assert "create:" in capsys.readouterr().out


def test_main_returns_failure_when_a_source_file_is_missing(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(obsidian_sync, "REPO_ROOT", tmp_path)

    assert obsidian_sync.main(["--vault-path", str(tmp_path / "vault")]) == 1
    assert "obsidian sync failed:" in capsys.readouterr().err
