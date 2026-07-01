# earth-pulse-poc

Earth Pulse proof-of-concept scripts for reading live seismic data from IRIS and
extracting slow microseism rhythms.

## Scripts

- `earth_period.py` computes the dominant primary microseism period.
- `collect_earth_period.py` appends one `earth_period.py` run to a JSONL journal.
- `earth_26s_detector.py` detects the faint narrow ~26-second microseism line
  near 0.0385 Hz using Welch PSD and adjacent-band SNR.
- `collect_earth_26s.py` appends one 26-second detector run to a JSONL journal
  and compares it with previous runs.

## Usage

```bash
pip install -r requirements.txt

python earth_period.py --hours 6 --verbose
python earth_26s_detector.py --hours 24 --verbose
python earth_26s_detector.py --hours 24 --plot
python collect_earth_26s.py --hours 6 --verbose
python generate_earth_pulse_json.py --hours 6 --output earth-pulse.json --verbose
```

The 26-second line is intermittent. A non-detection for a short or quiet window
is expected; use `--hours 12` to `--hours 24` for a stronger check.

## Serverless app feed

`earth-pulse.json` is the public feed for the app. GitHub Actions refreshes it
every 6 hours with `.github/workflows/update-earth-pulse.yml`.

The app should:

- use `breathing_rhythm` for the fixed 13s inhale / 13s exhale timer;
- use `app_pulse` for onboarding and the "Earth pulse today" card;
- fall back gracefully when `app_pulse.source` is `last_good_measurement` or
  `baseline`.

The exact JSON contract is documented in
`docs/earth-pulse-json-contract.md`.

## Repository boundary

This repository owns the Pulse of Earth product: seismic acquisition, signal
processing, collectors, the public JSON contract, and feed publication.

AI agent routing, operational verification, Linear/Obsidian synchronization,
and notifications are owned by
[`IIIH23/ai-orchestrator`](https://github.com/IIIH23/ai-orchestrator).
The repositories integrate through `orchestrator-project.yaml`; Orchestrator is
a control plane and is not required at runtime to serve `earth-pulse.json`.

See `docs/ai-orchestrator-integration.md` for the ownership and infrastructure
boundary.
