# Pulse of Earth application

Place the application source in this directory.

The directory is intentionally framework-neutral. When the application source
is added, keep its package manifest, lockfile, platform configuration, tests,
and build instructions here.

## Integration contract

- Read the feed URL from `PULSE_FEED_URL`.
- Use `fixtures/earth-pulse.sample.json` for offline UI development.
- Validate production responses against
  `contracts/earth-pulse.schema.json`.
- Use `breathing_rhythm` for the timer and `app_pulse` for display.
- Treat an expired feed as stale but continue to support the fixed breathing
  rhythm.
- Handle all three sources: `current_measurement`,
  `last_good_measurement`, and `baseline`.

Copy the repository-level `.env.example` into the configuration mechanism
supported by the selected framework. Do not commit credentials or local
environment files.

## Required commands

After selecting the framework, document and automate equivalent commands for:

1. dependency installation;
2. linting and type checking;
3. unit tests;
4. a production build;
5. a local development server or simulator;
6. an end-to-end smoke test.
