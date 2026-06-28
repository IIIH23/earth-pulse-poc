#!/usr/bin/env bash
# Health check script for Pulse of Earth staging
# Run as deploy user or root
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$(cd -- "$SCRIPT_DIR/.." && pwd)}"
HEALTH_ENDPOINT="${HEALTH_ENDPOINT:-http://127.0.0.1:8080/health}"
HEALTHCHECK_SCRIPT="$PROJECT_ROOT/tools/healthcheck.py"
ALERT_SCRIPT="${ALERT_SCRIPT:-$PROJECT_ROOT/tools/telegram_notify.py}"

pass=0
fail=0

check() {
  local name="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    echo "PASS  $name"
    pass=$((pass+1))
  else
    echo "FAIL  $name"
    fail=$((fail+1))
  fi
}

# Python-backed system health checks
health_json=""
if health_json="$(python3 "$HEALTHCHECK_SCRIPT" --json)"; then
  health_exit=0
else
  health_exit=$?
fi

health_records=()
if mapfile -t health_records < <(
  python3 -c '
import json
import sys

payload = json.load(sys.stdin)
checks = payload["checks"]
passed = sum(bool(check["passed"]) for check in checks)
failed = len(checks) - passed
print(f"{passed} {failed}")
for check in checks:
    status = "PASS" if check["passed"] else "FAIL"
    print(f"{status}  {check['"'"'name'"'"']}")
' <<<"$health_json"
) && ((${#health_records[@]} > 0)); then
  read -r health_pass health_fail <<<"${health_records[0]}"
  for result in "${health_records[@]:1}"; do
    echo "$result"
  done
  pass=$((pass + health_pass))
  fail=$((fail + health_fail))
else
  echo "FAIL  Python health checks (exit code $health_exit)"
  fail=$((fail + 1))
fi

# HTTP health
check "app responds on /health" curl -fsS "$HEALTH_ENDPOINT"

# Security
check "fail2ban running" systemctl is-active fail2ban

# Summary
echo ""
echo "Health: $pass PASS, $fail FAIL"

if [ "$fail" -gt 0 ]; then
  if [ -f "$ALERT_SCRIPT" ]; then
    python3 "$ALERT_SCRIPT" \
      --severity warning \
      --message "Staging health check failed: $fail failures" || true
  fi
  exit 1
fi

if [[ -v NOTIFY_SUCCESS && -f "$ALERT_SCRIPT" ]]; then
  python3 "$ALERT_SCRIPT" \
    --severity success \
    --message "Staging health check passed" || true
fi

exit 0
