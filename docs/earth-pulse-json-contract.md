# Earth Pulse JSON Contract

`earth-pulse.json` is the public, serverless API for the app. GitHub Actions
refreshes it every 6 hours by running the 26-second detector.

The machine-readable JSON Schema is
`contracts/earth-pulse.schema.json`. Application fixtures and the published feed
are validated against it in CI.

Public URL shape:

```text
https://raw.githubusercontent.com/IIIH23/earth-pulse-poc/main/earth-pulse.json
```

## App Rules

- Use `breathing_rhythm` for the session timer. It is always fixed at 13 seconds
  inhale and 13 seconds exhale.
- Use `app_pulse` for onboarding and the "Earth pulse today" card.
- If `app_pulse.source` is `current_measurement`, the current detector run was
  confirmed by at least 2 stations.
- If `app_pulse.source` is `last_good_measurement`, the latest run was weak or
  missing, and the app is using the previous confirmed reading.
- If `app_pulse.source` is `baseline`, no confirmed reading exists yet. The app
  should avoid "measured just now" copy and say approximately 26 seconds.
- Treat the JSON as stale when `expires_at_utc` is in the past. The app can still
  use `breathing_rhythm`.

## Top-Level Fields

```json
{
  "schema_version": "1.0.0",
  "generated_at_utc": "2026-06-24T19:10:00+00:00",
  "expires_at_utc": "2026-06-25T07:10:00+00:00",
  "app_pulse": {},
  "breathing_rhythm": {},
  "current_measurement": {},
  "last_good_measurement": {},
  "history": []
}
```

## `app_pulse`

The compact value the app should display as the live Earth pulse.

```json
{
  "source": "current_measurement",
  "period_s": 26.6,
  "frequency_hz": 0.03759,
  "fresh": true,
  "measured_at_utc": "2026-06-24T18:59:21+00:00"
}
```

`source` is one of:

- `current_measurement`
- `last_good_measurement`
- `baseline`

## `breathing_rhythm`

The product rhythm. This is intentionally fixed.

```json
{
  "mode": "fixed_13_13",
  "period_s": 26.0,
  "inhale_s": 13.0,
  "exhale_s": 13.0,
  "locked": true
}
```

## `current_measurement`

The latest 26-second detector run.

```json
{
  "measured_at_utc": "2026-06-24T18:59:21+00:00",
  "window_hours": 6.0,
  "target_frequency_hz": 0.038461538461538464,
  "target_period_s": 26.0,
  "target_band_hz": [0.036, 0.041],
  "background_bands_hz": [[0.028, 0.0345], [0.0425, 0.049]],
  "snr_threshold": 3.0,
  "detected": true,
  "quality_status": "confirmed",
  "confidence_label": "high (multiple stations, tight agreement)",
  "period_s": 26.6,
  "frequency_hz": 0.03759,
  "stations_detected": 2,
  "stations_attempted": 6,
  "station_errors": 0,
  "best_station": {},
  "median_snr": 1.68,
  "stations": []
}
```

`quality_status` is one of:

- `confirmed`: 2 or more stations crossed the SNR threshold and produced a
  consensus period.
- `weak_single_station`: 1 station crossed the SNR threshold.
- `not_detected`: no station crossed the threshold in this window.

## Station Object

```json
{
  "code": "II.SHEL",
  "label": "St. Helena, South Atlantic",
  "period_s": 26.08,
  "frequency_hz": 0.03834,
  "snr": 5.37,
  "detected": true,
  "error": null
}
```

## `last_good_measurement`

The most recent `confirmed` measurement. It is updated only when the current run
has `quality_status: confirmed`.

## `history`

Rolling compact history, newest entry last. The generator keeps the latest 24
entries by default.
