# Port: tools/telegram_notify.py

Selected source: `scripts/send-telegram-alert.sh`

## Rationale

- The alerting script is reused by `check-health.sh`, `rollback.sh`, and (planned) monitoring workflows — a good consolidation target for a single Python module.
- Its inputs/outputs are well-defined: severity + message + details → Telegram sendMessage API call.
- It uses `curl` and shell-only string manipulation; wrapping it in a small Python CLI allows `--dry-run`, structured input (JSON stdin/env), and consistent behavior across platforms.
- Zero external deps: only `urllib.request` from stdlib.

## Scope

A single Python script `tools/telegram_notify.py` that:

1. Accepts CLI arguments: `--severity` (critical|warning|success|info), `--message`, `--details`, `--dry-run`.
2. Reads config from env: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
3. Falls back to a config file: `$TELEGRAM_NOTIFY_CONFIG` (JSON file with `{bot_token, chat_id, env}`).
4. Inputs: severity, message, details.
5. Outputs: JSON summary of the action (sent/dry-run/error).
6. Env placeholders: `[ENV]` is replaced with `$TELEGRAM_ENV_NAME` (default `production`).
7. Telegram parse mode: `Markdown`.
8. Truncate payload to 4096 chars (Telegram limit).
9. Exit 0 on success, exit 1 on failure (invalid input, non-2xx response).

## Inputs

- `--severity`: one of critical | warning | success | info
- `--message`: short alert message (required)
- `--details`: optional block of text with extra context
- `--dry-run`: print the JSON payload instead of sending
- `--config`: path to JSON config file with `bot_token`, `chat_id`, `env`
- Environment: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `TELEGRAM_ENV_NAME`, `TELEGRAM_NOTIFY_CONFIG`

## Outputs

- JSON to stdout: `{"sent": true, "length": N, ...}` or `{"sent": false, "dry_run": true, "payload": "..."}` or `{"error": "..."}`.
- Telegram HTTP call via POST to `https://api.telegram.org/bot<TOKEN>/sendMessage`.
- Exit code 0 on send success or dry-run; 1 on any config or API error.

## Verification

- `python3 -m py_compile tools/telegram_notify.py` — no syntax errors.
- `python3 -m pytest tests/test_telegram_notify.py -q` — all tests green.
- Tests use `tmp_path` + monkeypatch + mocking `urllib.request.urlopen`.

## Implementation constraints

- Python 3.11 stdlib only (argparse, json, os, sys, urllib.request, typing).
- Type hints on all public functions.
- Explicit error messages when `TELEGRAM_BOT_TOKEN` or `TELEGRAM_CHAT_ID` missing.
- Write tests using plain `unittest.mock` (no pytest fixtures if it complicates).

## Next Steps

After implementation:
1. Run `python3 -m pytest tests/test_telegram_notify.py -q`.
2. Update `scripts/check-health.sh` and `scripts/rollback.sh` to call `python3 tools/telegram_notify.py` as their alerting backend.
3. Update CI workflow if appropriate (likely no — CI doesn't send messages).
