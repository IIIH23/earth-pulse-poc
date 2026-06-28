"""Tests for the daily healthcheck report workflow."""

from __future__ import annotations

import json
from unittest.mock import patch

from tools import healthcheck_report


HEALTHY = [
    ("disk", True, "ok"),
    ("memory", True, "ok"),
]
UNHEALTHY = [
    ("disk", True, "ok"),
    ("memory", False, "low"),
]


def _telegram_config(tmp_path):
    path = tmp_path / "telegram.json"
    path.write_text(
        json.dumps(
            {"bot_token": "token", "chat_id": "123", "env_name": "test"}
        ),
        encoding="utf-8",
    )
    return path


def test_all_healthy_exits_zero_and_uses_success_severity(tmp_path):
    config = _telegram_config(tmp_path)
    with (
        patch("tools.healthcheck_report.run_checks", return_value=HEALTHY),
        patch(
            "tools.healthcheck_report.send_message",
            return_value={"sent": True},
        ) as send,
    ):
        code = healthcheck_report.main(
            ["--destination", "telegram", "--config", str(config)]
        )

    assert code == 0
    assert send.call_args.args[0] == "success"


def test_one_failure_exits_one_and_uses_critical_severity(tmp_path):
    config = _telegram_config(tmp_path)
    with (
        patch("tools.healthcheck_report.run_checks", return_value=UNHEALTHY),
        patch(
            "tools.healthcheck_report.send_message",
            return_value={"sent": True},
        ) as send,
    ):
        code = healthcheck_report.main(
            ["--destination", "telegram", "--config", str(config)]
        )

    assert code == 1
    assert send.call_args.args[0] == "critical"


def test_stdout_destination_prints_report(capsys):
    with patch("tools.healthcheck_report.run_checks", return_value=HEALTHY):
        code = healthcheck_report.main(["--destination", "stdout"])

    output = capsys.readouterr().out
    assert code == 0
    assert "PASS  disk" in output
    assert "Health: 2 PASS, 0 FAIL" in output


def test_dry_run_does_not_call_send_message(capsys):
    with (
        patch("tools.healthcheck_report.run_checks", return_value=HEALTHY),
        patch("tools.healthcheck_report.send_message") as send,
    ):
        code = healthcheck_report.main(
            ["--destination", "telegram", "--dry-run"]
        )

    assert code == 0
    assert "Health: 2 PASS, 0 FAIL" in capsys.readouterr().out
    send.assert_not_called()


def test_delivery_retries_twice_then_succeeds(tmp_path):
    config = _telegram_config(tmp_path)
    with (
        patch("tools.healthcheck_report.run_checks", return_value=HEALTHY),
        patch(
            "tools.healthcheck_report.send_message",
            side_effect=[OSError("one"), OSError("two"), {"sent": True}],
        ) as send,
        patch("tools.healthcheck_report.time.sleep") as sleep,
    ):
        code = healthcheck_report.main(
            ["--destination", "telegram", "--config", str(config)]
        )

    assert code == 0
    assert send.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [30, 60]


def test_delivery_failure_after_three_attempts_exits_two(tmp_path):
    config = _telegram_config(tmp_path)
    with (
        patch("tools.healthcheck_report.run_checks", return_value=HEALTHY),
        patch(
            "tools.healthcheck_report.send_message",
            side_effect=OSError("offline"),
        ) as send,
        patch("tools.healthcheck_report.time.sleep"),
    ):
        code = healthcheck_report.main(
            ["--destination", "telegram", "--config", str(config)]
        )

    assert code == 2
    assert send.call_count == 3


def test_invalid_destination_exits_three():
    assert healthcheck_report.main(["--destination", "email"]) == 3


def test_file_destination_appends_json_line(tmp_path):
    output = tmp_path / "health.jsonl"
    output.write_text('{"existing": true}\n', encoding="utf-8")

    with patch("tools.healthcheck_report.run_checks", return_value=UNHEALTHY):
        code = healthcheck_report.main(
            ["--destination", "file", "--output-file", str(output)]
        )

    lines = output.read_text(encoding="utf-8").splitlines()
    report = json.loads(lines[-1])
    assert code == 1
    assert len(lines) == 2
    assert report["timestamp"]
    assert report["summary"] == {
        "passed": 1,
        "failed": 1,
        "healthy": False,
    }
    assert report["checks"][1] == {
        "name": "memory",
        "passed": False,
        "detail": "low",
    }
