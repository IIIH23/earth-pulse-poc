# Contributing

## Setup

```bash
python -m venv .venv
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Change boundaries

- Product and detector changes belong in this repository.
- AI orchestration and cross-repository automation belong in
  `IIIH23/ai-orchestrator`.
- Changes to `earth-pulse.json` structure must update the JSON Schema,
  documentation, fixtures, and contract tests in the same pull request.
- Application changes belong under `apps/pulse-of-earth/`.

Run the relevant lint, tests, and build locally before opening a pull request.
Do not commit local downloads, generated build output, credentials, or
environment files.
