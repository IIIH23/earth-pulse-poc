#!/usr/bin/env python3
"""Mirror canonical project state into an Obsidian-readable directory."""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VAULT_PATH = REPO_ROOT / "docs" / "obsidian"
LOG_HEADING = re.compile(
    r"^## (?P<date>\d{4}-\d{2}-\d{2})(?:[T ][^\n]*)?$",
    re.MULTILINE,
)


@dataclass(frozen=True)
class SyncResult:
    """Describe the result of synchronizing one destination file."""

    path: Path
    action: str


def extract_recent_log_entries(log_text: str) -> tuple[date, str]:
    """Return all log sections belonging to the latest date in *log_text*."""
    matches = list(LOG_HEADING.finditer(log_text))
    if not matches:
        raise ValueError("autopilot log contains no dated entries")

    sections: list[tuple[date, str]] = []
    for index, match in enumerate(matches):
        try:
            entry_date = date.fromisoformat(match.group("date"))
        except ValueError as error:
            raise ValueError(
                f"autopilot log contains an invalid date: {match.group('date')}"
            ) from error

        end = matches[index + 1].start() if index + 1 < len(matches) else len(log_text)
        sections.append((entry_date, log_text[match.start() : end].strip()))

    latest_date = max(entry_date for entry_date, _ in sections)
    recent_sections = [
        section for entry_date, section in sections if entry_date == latest_date
    ]
    rendered = f"# Autopilot Log — {latest_date.isoformat()}\n\n"
    rendered += "\n\n".join(recent_sections)
    return latest_date, f"{rendered.rstrip()}\n"


def _sync_file(path: Path, content: str, *, dry_run: bool) -> SyncResult:
    """Write *content* when needed and report the resulting action."""
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return SyncResult(path, "unchanged")

    action = "update" if path.exists() else "create"
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return SyncResult(path, action)


def sync_to_obsidian(
    repo_root: Path,
    vault_path: Path,
    *,
    dry_run: bool = False,
) -> list[SyncResult]:
    """Mirror canonical state, roadmap, and latest daily log into *vault_path*."""
    state = (repo_root / "AUTOPILOT_STATE.md").read_text(encoding="utf-8")
    roadmap = (repo_root / "ROADMAP.md").read_text(encoding="utf-8")
    log_text = (repo_root / "logs" / "AUTOPILOT_LOG.md").read_text(encoding="utf-8")
    log_date, recent_log = extract_recent_log_entries(log_text)

    files = (
        (vault_path / "STATE.md", state),
        (vault_path / "ROADMAP.md", roadmap),
        (vault_path / f"LOG-{log_date.isoformat()}.md", recent_log),
    )
    return [
        _sync_file(path, content, dry_run=dry_run) for path, content in files
    ]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=DEFAULT_VAULT_PATH,
        help="destination directory (default: docs/obsidian in the repository)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show planned changes without writing files",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the Obsidian mirror and return a process exit code."""
    args = parse_args(argv)
    try:
        results = sync_to_obsidian(
            REPO_ROOT,
            args.vault_path.expanduser(),
            dry_run=args.dry_run,
        )
    except (OSError, ValueError) as error:
        print(f"obsidian sync failed: {error}", file=sys.stderr)
        return 1

    prefix = "[dry-run] " if args.dry_run else ""
    for result in results:
        print(f"{prefix}{result.action}: {result.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
