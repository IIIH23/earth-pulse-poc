"""Tests for the Telegram notification tool."""

from __future__ import annotations

import json
from unittest.mock import Mock

import pytest

from tools import telegram_notify


@pytest.fixture
def telegram_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-12345")
    monkeypatch.setenv("TELEGRAM_ENV_NAME", "staging")


def test_missing_configuration_outputs_error(monkeypatch, capsys):
    for name in (
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_CHAT_ID",
        "TELEGRAM_ENV_NAME",
    ):
        monkeypatch.delenv(name, raising=False)

    exit_code = telegram_notify.main(["--message", "Unavailable"])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "error" in json.loads(captured.out)
    assert "token" in captured.err.lower()


def test_dry_run_outputs_payload_without_urlopen(
    telegram_env, monkeypatch, capsys
):
    urlopen = Mock(side_effect=AssertionError("urlopen must not be called"))
    monkeypatch.setattr(telegram_notify.urllib.request, "urlopen", urlopen)

    exit_code = telegram_notify.main(
        ["--severity", "warning", "--message", "High load", "--dry-run"]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["sent"] is False
    assert output["dry_run"] is True
    assert output["payload"]
    urlopen.assert_not_called()


def test_message_includes_severity_environment_and_text(telegram_env, capsys):
    telegram_notify.main(
        ["--severity", "critical", "--message", "Database is down", "--dry-run"]
    )

    payload = json.loads(capsys.readouterr().out)["payload"]
    assert payload.startswith("[CRITICAL]\nEnvironment: staging\n")
    assert payload.endswith("Database is down")


def test_long_payload_is_shortened_to_limit():
    payload = telegram_notify.build_message("info", "x" * 5000, "production")

    assert len(payload) == telegram_notify.MAX_MESSAGE_LENGTH
    assert payload.startswith("[INFO]\nEnvironment: production\n")


def test_details_append_markdown_fenced_block():
    payload = telegram_notify.build_message(
        "success", "Backup completed", "production", "files: 42"
    )

    assert payload.endswith("```\nfiles: 42\n```")


def test_successful_send_outputs_sent_true(telegram_env, monkeypatch, capsys):
    response = Mock()
    urlopen = Mock(return_value=response)
    monkeypatch.setattr(telegram_notify.urllib.request, "urlopen", urlopen)

    exit_code = telegram_notify.main(
        ["--severity", "success", "--message", "Deploy completed"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert json.loads(captured.out) == {"sent": True}
    assert "sending message" in captured.err
    urlopen.assert_called_once()
    response.read.assert_called_once_with()
    response.close.assert_called_once_with()


def test_send_uses_post_and_form_encoded_fields(
    telegram_env, monkeypatch, capsys
):
    monkeypatch.setattr(
        telegram_notify.urllib.request,
        "urlopen",
        Mock(return_value=Mock()),
    )

    telegram_notify.main(["--message", "Wind & rain"])
    request = telegram_notify.urllib.request.urlopen.call_args.args[0]

    assert request.get_method() == "POST"
    assert request.full_url.endswith("/bottest-token/sendMessage")
    assert b"chat_id=-12345" in request.data
    assert b"text=%5BINFO%5D%0AEnvironment%3A+staging%0AWind+%26+rain" in request.data
    assert b"parse_mode=Markdown" in request.data
    assert json.loads(capsys.readouterr().out) == {"sent": True}


def test_send_failure_outputs_error(telegram_env, monkeypatch, capsys):
    monkeypatch.setattr(
        telegram_notify.urllib.request,
        "urlopen",
        Mock(side_effect=OSError("network unavailable")),
    )

    exit_code = telegram_notify.main(["--message", "Deploy failed"])

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert output == {"error": "network unavailable"}


def test_send_failure_does_not_expose_bot_token(
    telegram_env, monkeypatch, capsys
):
    monkeypatch.setattr(
        telegram_notify.urllib.request,
        "urlopen",
        Mock(
            side_effect=OSError(
                "request failed: "
                "https://api.telegram.org/bottest-token/sendMessage"
            )
        ),
    )

    telegram_notify.main(["--message", "Deploy failed"])

    captured = capsys.readouterr()
    assert "test-token" not in captured.out
    assert "test-token" not in captured.err
    assert "[REDACTED]" in json.loads(captured.out)["error"]


def test_config_file_takes_priority_over_environment(
    telegram_env, tmp_path, capsys
):
    config_path = tmp_path / "telegram.json"
    config_path.write_text(
        json.dumps(
            {
                "bot_token": "config-token",
                "chat_id": "987",
                "env_name": "production",
            }
        ),
        encoding="utf-8",
    )

    exit_code = telegram_notify.main(
        ["--config", str(config_path), "--message", "Ready", "--dry-run"]
    )

    payload = json.loads(capsys.readouterr().out)["payload"]
    assert exit_code == 0
    assert "Environment: production" in payload


def test_config_can_fall_back_to_environment(
    telegram_env, tmp_path, capsys
):
    config_path = tmp_path / "telegram.json"
    config_path.write_text('{"env_name": "qa"}', encoding="utf-8")

    exit_code = telegram_notify.main(
        ["--config", str(config_path), "--message", "Ready", "--dry-run"]
    )

    payload = json.loads(capsys.readouterr().out)["payload"]
    assert exit_code == 0
    assert "Environment: qa" in payload


def test_invalid_config_file_outputs_error(telegram_env, tmp_path, capsys):
    config_path = tmp_path / "telegram.json"
    config_path.write_text("not-json", encoding="utf-8")

    exit_code = telegram_notify.main(
        ["--config", str(config_path), "--message", "Ready"]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert "unable to read config" in output["error"]
