#!/usr/bin/env python3
"""Run health checks and deliver a daily report."""

from __future__ import annotations

import argparse
import inspect
import json
import sys
import time
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path so ``tools.*`` imports work
# when this script is executed directly (e.g. ``python3 tools/healthcheck_report.py``).
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from tools.healthcheck import format_text, run_checks
from tools.telegram_notify import send_message


CheckResult = tuple[str, bool, str]
MAX_DELIVERY_ATTEMPTS = 3
RETRY_DELAYS_SECONDS = (30, 60)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run and deliver the Pulse of Earth daily healthcheck report."
    )
    parser.add_argument(
        "--destination",
        choices=("telegram", "stdout", "file"),
        default="stdout",
    )
    parser.add_argument("--config", help="path to Telegram JSON configuration")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-file", help="JSON Lines file for file delivery")
    return parser


def _load_telegram_config(path: str | None) -> dict[str, str]:
    if path is None:
        raise ValueError("--config is required for telegram destination")

    try:
        with open(path, encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, ValueError) as error:
        raise ValueError(f"unable to read Telegram config: {error}") from error

    if not isinstance(config, dict):
        raise ValueError("Telegram config must contain a JSON object")

    token = config.get("bot_token")
    chat_id = config.get("chat_id")
    env_name = config.get("env_name", "unknown")
    if not isinstance(token, str) or not token.strip():
        raise ValueError("Telegram config requires bot_token")
    if not isinstance(chat_id, (str, int)) or not str(chat_id).strip():
        raise ValueError("Telegram config requires chat_id")
    if not isinstance(env_name, str):
        raise ValueError("Telegram config env_name must be a string")

    return {
        "bot_token": token.strip(),
        "chat_id": str(chat_id).strip(),
        "env_name": env_name.strip() or "unknown",
    }


def _telegram_delivery(
    severity: str,
    report: str,
    config: dict[str, str],
) -> None:
    """Send using either the workflow-level or legacy low-level API."""
    parameters = tuple(inspect.signature(send_message).parameters)
    if parameters[:2] == ("token", "chat_id"):
        message = (
            f"[{severity.upper()}]\n"
            f"Environment: {config['env_name']}\n"
            "Daily Healthcheck Report\n"
            f"```\n{report}\n```"
        )
        send_message(config["bot_token"], config["chat_id"], message)
        return

    response = send_message(
        severity,
        "Daily Healthcheck Report",
        report,
        dry_run=False,
    )
    if isinstance(response, dict) and (
        response.get("error") or response.get("sent") is False
    ):
        raise RuntimeError(str(response.get("error") or "message was not sent"))


def _file_payload(results: Sequence[CheckResult]) -> dict[str, Any]:
    passed = sum(result[1] for result in results)
    failed = len(results) - passed
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": [
            {"name": name, "passed": check_passed, "detail": detail}
            for name, check_passed, detail in results
        ],
        "summary": {
            "passed": passed,
            "failed": failed,
            "healthy": failed == 0,
        },
    }


def _append_report(path: str, results: Sequence[CheckResult]) -> None:
    with open(Path(path), "a", encoding="utf-8") as output_file:
        output_file.write(json.dumps(_file_payload(results)) + "\n")


def _deliver_with_retries(deliver: Callable[[], None]) -> bool:
    for attempt in range(MAX_DELIVERY_ATTEMPTS):
        try:
            deliver()
            return True
        except Exception as error:
            if attempt == MAX_DELIVERY_ATTEMPTS - 1:
                print(
                    f"healthcheck_report: delivery failed after "
                    f"{MAX_DELIVERY_ATTEMPTS} attempts: {error}",
                    file=sys.stderr,
                )
                return False
            time.sleep(RETRY_DELAYS_SECONDS[attempt])
    return False


def main(argv: Sequence[str] | None = None) -> int:
    """Collect checks, deliver their report, and return a workflow exit code."""
    try:
        args = _parser().parse_args(argv)
    except SystemExit:
        return 3

    if args.destination == "file" and not args.output_file:
        print(
            "healthcheck_report: --output-file is required for file destination",
            file=sys.stderr,
        )
        return 3

    telegram_config: dict[str, str] | None = None
    if args.destination == "telegram" and not args.dry_run:
        try:
            telegram_config = _load_telegram_config(args.config)
        except ValueError as error:
            print(f"healthcheck_report: {error}", file=sys.stderr)
            return 3

    try:
        results = run_checks()
    except Exception as error:
        results = [
            (
                "health check collection",
                False,
                f"collection raised {type(error).__name__}: {error}",
            )
        ]

    report = format_text(results, args.verbose)
    healthy = all(passed for _, passed, _ in results)

    if args.dry_run:
        print(report)
        return 0 if healthy else 1

    if args.destination == "stdout":
        print(report)
        delivered = True
    elif args.destination == "file":
        delivered = _deliver_with_retries(
            lambda: _append_report(args.output_file, results)
        )
    else:
        severity = "success" if healthy else "critical"
        assert telegram_config is not None
        delivered = _deliver_with_retries(
            lambda: _telegram_delivery(severity, report, telegram_config)
        )

    if not delivered:
        return 2
    return 0 if healthy else 1


if __name__ == "__main__":
    raise SystemExit(main())
