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
```

The 26-second line is intermittent. A non-detection for a short or quiet window
is expected; use `--hours 12` to `--hours 24` for a stronger check.
