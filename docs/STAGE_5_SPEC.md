# Stage 5 — Deterministic Workflows With n8n

> Status: 🔄 In Progress
> Selected workflow: **Daily Healthcheck Report**

## Workflow Selection

From the 4 candidates in `docs/N8N.md`, the **Daily Healthcheck Report** is chosen as the first workflow because:

1. It reuses already-ported Stage 2 logic (`tools/healthcheck.py`, `tools/telegram_notify.py`)
2. It has a simple, deterministic trigger (schedule-based)
3. It can be implemented and tested locally without external n8n infrastructure
4. It delivers immediate operational value (daily visibility into system health)

## Workflow: Daily Healthcheck Report

### Trigger

- **Type**: Scheduled (cron-style)
- **Frequency**: Daily at 08:00 UTC
- **Implementation**: A Python CLI tool (`tools/healthcheck_report.py`) that can be invoked by cron, n8n, or manually

### Inputs

| Input | Source | Required |
| --- | --- | --- |
| `--destination` | CLI arg (telegram, stdout, file) | Yes (default: stdout) |
| `--config` | Path to JSON config with Telegram credentials | Only for telegram destination |
| `--verbose` | CLI flag — include passing check details | No |
| `--dry-run` | CLI flag — collect checks but don't send | No |

### Steps

1. **Collect**: Run all checks from `tools.healthcheck.run_checks()` (disk, memory, docker, ufw)
2. **Format**: Build a human-readable summary with emoji status indicators
3. **Evaluate**: Determine overall health (healthy if all checks pass)
4. **Deliver**: Send to configured destination:
   - `telegram`: Send via `tools.telegram_notify.send_message()` with severity based on health
   - `stdout`: Print formatted report to console
   - `file`: Append JSON report to a local file (for log aggregation)
5. **Exit**: Return 0 if healthy, 1 if any check failed (for cron/n8n error detection)

### Outputs

- **Telegram message**: Formatted health report with PASS/FAIL per check
- **stdout**: Human-readable text report (same format as Telegram)
- **file**: JSON line with full check results + timestamp
- **Exit code**: 0 (healthy) or 1 (any failure)

### Retry Policy

| Attempt | Action |
| --- | --- |
| 1 | Run checks, attempt delivery |
| 2 (on delivery failure) | Retry after 30s |
| 3 (on delivery failure) | Retry after 60s, then give up |

Max 3 attempts. Check collection failures are NOT retried (they indicate real system state).

### Failure Handling

- **Check collection fails**: Report partial results, mark as degraded, exit 1
- **Delivery fails after retries**: Log error to stderr, exit 2 (distinct from check failure)
- **Invalid config**: Print usage error, exit 3

### Exit Codes

| Code | Meaning |
| --- | --- |
| 0 | All checks passed, delivery successful |
| 1 | One or more checks failed, delivery successful |
| 2 | Checks completed, delivery failed after retries |
| 3 | Configuration or argument error |

## Implementation

- `tools/healthcheck_report.py` — workflow runner (stdlib-only Python CLI)
- `tests/test_healthcheck_report.py` — pytest tests with mocked checks and delivery

## Verification

- `python3 -m pytest tests/test_healthcheck_report.py -q` — all tests green
- `python3 tools/healthcheck_report.py --destination stdout --verbose` — manual smoke test
- `python3 tools/healthcheck_report.py --dry-run` — verify no external calls

## Future Workflows

After this workflow is stable, the next candidates from `docs/N8N.md`:

1. **GitHub PR Merged → Linear Update** (requires n8n + Linear API)
2. **Deployment Failed → Alert** (requires GitHub Actions integration)
3. **Backup Verification** (requires backup infrastructure)
