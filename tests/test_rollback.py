"""Tests for the rollback command-line tool."""

from __future__ import annotations

import subprocess

import pytest

from tools import rollback


@pytest.mark.parametrize(
    ("argv", "command"),
    [
        (["current"], "current"),
        (["list"], "list"),
        (["rollback"], "rollback"),
    ],
)
def test_parse_args_recognizes_subcommands(argv, command):
    assert rollback.parse_args(argv).command == command


def test_parse_args_rollback_defaults_to_staging():
    assert rollback.parse_args(["rollback"]).tag == "staging"


def test_parse_args_accepts_rollback_tag():
    assert rollback.parse_args(["rollback", "sha-abc123"]).tag == "sha-abc123"


def test_parse_args_accepts_paths_and_flags(tmp_path):
    args = rollback.parse_args(
        [
            "--state-dir",
            str(tmp_path / "state"),
            "--compose-file",
            str(tmp_path / "compose.yaml"),
            "--log-file",
            str(tmp_path / "rollback.log"),
            "--dry-run",
            "--exit-zero",
            "current",
        ]
    )

    assert args.state_dir == tmp_path / "state"
    assert args.compose_file == tmp_path / "compose.yaml"
    assert args.log_file == tmp_path / "rollback.log"
    assert args.dry_run is True
    assert args.exit_zero is True


def test_current_runs_compose_and_writes_state(tmp_path, monkeypatch):
    commands = []

    def fake_run(command, **kwargs):
        commands.append((command, kwargs))
        return subprocess.CompletedProcess(
            command, 0, '[{"Repository":"example","Tag":"sha-good"}]\n', ""
        )

    monkeypatch.setattr(rollback.subprocess, "run", fake_run)
    state_dir = tmp_path / "releases"

    exit_code = rollback.main(
        [
            "--state-dir",
            str(state_dir),
            "--compose-file",
            str(tmp_path / "compose.yaml"),
            "--log-file",
            str(tmp_path / "rollback.log"),
            "current",
        ]
    )

    assert exit_code == 0
    assert commands[0][0] == [
        "docker",
        "compose",
        "-f",
        str(tmp_path / "compose.yaml"),
        "images",
        "--format",
        "json",
    ]
    assert commands[0][1]["timeout"] == rollback.COMMAND_TIMEOUT_SECONDS
    assert "RELEASE_TAG=sha-good" in (
        state_dir / "last-good-release.txt"
    ).read_text(encoding="utf-8")


def test_list_runs_docker_and_filters_tags(monkeypatch, capsys):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(
            command, 0, "staging\nsha-one\nlatest\nsha-two\n", ""
        )

    monkeypatch.setattr(rollback.subprocess, "run", fake_run)

    assert rollback.main(["list"]) == 0
    assert commands == [
        [
            "docker",
            "image",
            "ls",
            rollback.IMAGE_REPOSITORY,
            "--format",
            "{{.Tag}}",
        ]
    ]
    output = capsys.readouterr().out
    assert "staging (current)" in output
    assert "sha-one" in output
    assert "sha-two" in output
    assert "\nlatest\n" not in output


def test_rollback_runs_expected_commands(tmp_path, monkeypatch):
    commands = []

    def fake_run(command, **kwargs):
        commands.append(command)
        stdout = '[{"tag":"sha-current"}]' if "images" in command else ""
        return subprocess.CompletedProcess(command, 0, stdout, "")

    monkeypatch.setattr(rollback.subprocess, "run", fake_run)
    monkeypatch.setattr(rollback.time, "sleep", lambda seconds: None)
    compose_file = tmp_path / "compose.yaml"

    exit_code = rollback.main(
        [
            "--state-dir",
            str(tmp_path / "state"),
            "--compose-file",
            str(compose_file),
            "--log-file",
            str(tmp_path / "rollback.log"),
            "rollback",
            "sha-target",
        ]
    )

    assert exit_code == 0
    assert commands == [
        [
            "docker",
            "compose",
            "-f",
            str(compose_file),
            "images",
            "--format",
            "json",
        ],
        ["docker", "compose", "-f", str(compose_file), "pull"],
        ["docker", "compose", "-f", str(compose_file), "up", "-d"],
        ["curl", "-fsS", rollback.HEALTH_URL],
    ]


def test_dry_run_executes_no_subprocesses(tmp_path, monkeypatch, capsys):
    def unexpected_run(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called in dry-run mode")

    monkeypatch.setattr(rollback.subprocess, "run", unexpected_run)
    log_file = tmp_path / "rollback.log"

    assert rollback.main(
        [
            "--state-dir",
            str(tmp_path / "state"),
            "--compose-file",
            str(tmp_path / "compose.yaml"),
            "--log-file",
            str(log_file),
            "--dry-run",
            "rollback",
            "sha-target",
        ]
    ) == 0
    assert not log_file.exists()
    assert "docker compose" in capsys.readouterr().out


def test_failure_returns_one_and_exit_zero_overrides(tmp_path, monkeypatch):
    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 1, "", "daemon unavailable")

    monkeypatch.setattr(rollback.subprocess, "run", fake_run)
    common = [
        "--log-file",
        str(tmp_path / "rollback.log"),
        "list",
    ]

    assert rollback.main(common) == 1
    assert rollback.main(["--exit-zero", *common]) == 0


def test_current_rejects_output_without_tag(tmp_path, monkeypatch):
    def fake_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 0, '{"Repository":"example"}', "")

    monkeypatch.setattr(rollback.subprocess, "run", fake_run)

    assert rollback.main(
        [
            "--state-dir",
            str(tmp_path / "state"),
            "--log-file",
            str(tmp_path / "rollback.log"),
            "current",
        ]
    ) == 1
