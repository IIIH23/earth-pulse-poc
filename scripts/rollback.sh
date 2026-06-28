#!/usr/bin/env bash
# Rollback script for Pulse of Earth staging
# Run as deploy user with docker access
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd -- "$SCRIPT_DIR/.." && pwd)}"
COMPOSE_FILE="${COMPOSE_FILE:-/opt/terrabits/apps/pulse-of-earth/compose.yaml}"
STATE_DIR="${STATE_DIR:-/opt/terrabits/releases}"
LOG_FILE="${LOG_FILE:-/opt/terrabits/backups/rollback.log}"
ROLLBACK_SCRIPT="$PROJECT_ROOT/tools/rollback.py"

case "${1:-help}" in
  current)
    command_args=(current)
    ;;
  list)
    command_args=(list)
    ;;
  rollback)
    command_args=(rollback "${2:-staging}")
    ;;
  *)
    echo "Usage: $0 {current|list|rollback [tag]}"
    exit 0
    ;;
esac

exec python3 "$ROLLBACK_SCRIPT" \
  --state-dir "$STATE_DIR" \
  --compose-file "$COMPOSE_FILE" \
  --log-file "$LOG_FILE" \
  "${command_args[@]}"
