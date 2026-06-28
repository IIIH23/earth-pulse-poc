#!/usr/bin/env bash
# Send Telegram alert
# Usage: send-telegram-alert.sh <severity> <message> [details]
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd -- "$SCRIPT_DIR/.." && pwd)}"
ALERT_SCRIPT="${ALERT_SCRIPT:-$PROJECT_ROOT/tools/telegram_notify.py}"

exec python3 "$ALERT_SCRIPT" \
  --severity "${1:-info}" \
  --message "${2:-No message}" \
  --details "${3:-}"
