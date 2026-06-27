#!/usr/bin/env python3
"""Send a formatted notification through the Telegram Bot API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from typing import Any, Mapping, Sequence


MAX_MESSAGE_LENGTH = 4096
DEFAULT_ENV_NAME = "unknown"
SEVERITIES = ("critical", "warning", "success", "info")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Send a Telegram notification.")
    parser.add_argument("--severity", choices=SEVERITIES, default="info")
    parser.add_argument("--message", required=True, help="short alert message")
    parser.add_argument(
        "--details",
        help="extra text to append in a Markdown-fenced code block",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the payload without sending it",
    )
    parser.add_argument("--config", help="path to a JSON configuration file")
    return parser.parse_args(argv)


def _read_config(path: str | None) -> dict[str, Any]:
    """Read and validate an optional JSON configuration file."""
    if path is None:
        return {}

    try:
        with open(path, encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, ValueError) as error:
        raise ValueError(f"unable to read config: {error}") from error

    if not isinstance(config, dict):
        raise ValueError("config must contain a JSON object")
    return config


def load_configuration(path: str | None) -> tuple[str, str, str]:
    """Load Telegram settings, preferring config values over environment values."""
    config = _read_config(path)
    token = config.get("bot_token") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = config.get("chat_id") or os.environ.get("TELEGRAM_CHAT_ID")
    env_name = (
        config.get("env_name")
        or os.environ.get("TELEGRAM_ENV_NAME")
        or DEFAULT_ENV_NAME
    )

    if not isinstance(token, str) or not token.strip():
        raise ValueError("Telegram bot token is not configured")
    if not isinstance(chat_id, (str, int)) or not str(chat_id).strip():
        raise ValueError("Telegram chat id is not configured")
    if not isinstance(env_name, str):
        raise ValueError("Telegram environment name must be a string")

    return token.strip(), str(chat_id).strip(), env_name.strip() or DEFAULT_ENV_NAME


def build_message(
    severity: str,
    message: str,
    env_name: str,
    details: str | None = None,
) -> str:
    """Build a Telegram message and constrain it to Telegram's length limit."""
    parts = [f"[{severity.upper()}]", f"Environment: {env_name}", message]
    if details is not None:
        parts.append(f"```\n{details}\n```")
    return "\n".join(parts)[:MAX_MESSAGE_LENGTH]


def _quote_form_value(value: str) -> str:
    """Percent-encode a value for application/x-www-form-urlencoded."""
    safe = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
    encoded: list[str] = []
    for byte in value.encode("utf-8"):
        if byte in safe:
            encoded.append(chr(byte))
        elif byte == 0x20:
            encoded.append("+")
        else:
            encoded.append(f"%{byte:02X}")
    return "".join(encoded)


def _form_data(fields: Mapping[str, str]) -> bytes:
    """Serialize fields as application/x-www-form-urlencoded bytes."""
    return "&".join(
        f"{_quote_form_value(key)}={_quote_form_value(value)}"
        for key, value in fields.items()
    ).encode("ascii")


def send_message(token: str, chat_id: str, message: str) -> None:
    """POST a message to the Telegram Bot API."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = _form_data(
        {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown",
            "disable_web_page_preview": "true",
        }
    )
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    response = urllib.request.urlopen(request, timeout=10)
    try:
        response.read()
    finally:
        response.close()


def _print_json(payload: Mapping[str, Any]) -> None:
    """Write one JSON object to stdout."""
    print(json.dumps(payload))


def main(argv: Sequence[str] | None = None) -> int:
    """Build and optionally send a Telegram notification."""
    args = parse_args(argv)
    token = ""

    try:
        token, chat_id, env_name = load_configuration(args.config)
    except (ValueError, OSError) as error:
        if not args.dry_run:
            print(f"telegram_notify: {error}", file=sys.stderr)
            _print_json({"error": str(error)})
            return 1

        env_name = "production"
        token = "dry-run-dummy"
        chat_id = "dry-run-dummy"

    try:
        message = build_message(args.severity, args.message, env_name, args.details)

        if args.dry_run:
            print("telegram_notify: dry run; message was not sent", file=sys.stderr)
            _print_json({"sent": False, "dry_run": True, "payload": message})
            return 0

        print("telegram_notify: sending message", file=sys.stderr)
        send_message(token, chat_id, message)
    except Exception as error:
        detail = str(error) or type(error).__name__
        if token:
            detail = detail.replace(token, "[REDACTED]")
        print(f"telegram_notify: {detail}", file=sys.stderr)
        _print_json({"error": detail})
        return 1

    _print_json({"sent": True})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
