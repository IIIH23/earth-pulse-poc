#!/usr/bin/env python3
"""Generate a Markdown inventory of files below a directory."""

from __future__ import annotations

import argparse
import fnmatch
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDES = (".git", "node_modules")
NOTABLE_DEV_FILES = (
    "Dockerfile",
    "docker-compose.yml",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "package.json",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a Markdown inventory of files below a root directory."
    )
    parser.add_argument("--root", type=Path, default=Path("."), help="directory to scan")
    parser.add_argument(
        "--depth",
        type=int,
        default=None,
        help="maximum directory depth (root-level files are depth 0)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="glob to exclude; may be specified more than once",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("audit/FILE_INVENTORY.md"),
        help="Markdown output path",
    )
    args = parser.parse_args()
    if args.depth is not None and args.depth < 0:
        parser.error("--depth must be zero or greater")
    return args


def is_excluded(relative_path: Path, patterns: Iterable[str]) -> bool:
    path_text = relative_path.as_posix()
    return any(
        fnmatch.fnmatch(relative_path.name, pattern)
        or fnmatch.fnmatch(path_text, pattern)
        for pattern in patterns
    )


def collect_files(
    root: Path, maximum_depth: int | None, exclude_patterns: Iterable[str]
) -> list[tuple[Path, int]]:
    files: list[tuple[Path, int]] = []

    for directory, directory_names, file_names in os.walk(root):
        directory_path = Path(directory)
        relative_directory = directory_path.relative_to(root)
        directory_depth = (
            0 if relative_directory == Path(".") else len(relative_directory.parts)
        )

        directory_names[:] = sorted(
            name
            for name in directory_names
            if not is_excluded(relative_directory / name, exclude_patterns)
            and (maximum_depth is None or directory_depth < maximum_depth)
        )

        for name in sorted(file_names):
            relative_path = relative_directory / name
            if is_excluded(relative_path, exclude_patterns):
                continue
            files.append((relative_path, (directory_path / name).stat().st_size))

    return sorted(files, key=lambda item: item[0].as_posix())


def render_inventory(root: Path, files: list[tuple[Path, int]]) -> str:
    present_root_files = {path.as_posix() for path, _ in files if len(path.parts) == 1}
    missing_dev_files = [
        name for name in NOTABLE_DEV_FILES if name not in present_root_files
    ]
    extensions = Counter(
        path.suffix.removeprefix(".").lower()
        for path, _ in files
        if path.suffix
    )
    top_extensions = ", ".join(
        extension
        for extension, _ in sorted(
            extensions.items(), key=lambda item: (-item[1], item[0])
        )[:5]
    )

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    lines = [
        "# File Inventory",
        "",
        f"Generated {generated_at} from `{root}`.",
        "",
        "## Summary",
        "",
        f"- Total files: {len(files)}",
        f"- Top file extensions: {top_extensions or 'none'}",
        "- Notable dev files missing: "
        + (", ".join(missing_dev_files) if missing_dev_files else "none"),
        "",
        "## Listing",
        "",
        "Path | Size",
        "--- | ---:",
    ]
    lines.extend(f"`{path.as_posix()}` | {size} bytes" for path, size in files)
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    try:
        root = args.root.resolve(strict=True)
        if not root.is_dir():
            raise NotADirectoryError(f"root is not a directory: {root}")

        patterns = (*DEFAULT_EXCLUDES, *args.exclude)
        files = collect_files(root, args.depth, patterns)
        output = args.out.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_inventory(root, files), encoding="utf-8")
    except OSError as error:
        print(f"inventory: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
