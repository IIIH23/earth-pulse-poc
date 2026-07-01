# Repository Structure

This repository is a monorepo for the Pulse of Earth product.

```text
apps/
  pulse-of-earth/        application source and offline fixtures
contracts/               machine-readable public feed contracts
docs/                    product, API, and integration documentation
tests/                   detector and feed-contract tests
*.py                     detector and publication scripts
earth-pulse.json         generated public feed
```

The detector scripts remain at the root for backward compatibility with the
scheduled workflow. Move them into `services/detector/` only as a separate
refactor that preserves CLI wrappers and the feed workflow.

AI Orchestrator is a separate control-plane repository. It can inspect and
coordinate this repository, but the application and detector source remain
here.

## Application upload checklist

- Put application code under `apps/pulse-of-earth/`.
- Commit the framework lockfile.
- Add framework-specific lint, test, build, and E2E jobs to CI.
- Read the feed URL from environment configuration.
- Validate fixture and remote-feed parsing against the JSON Schema.
- Document local development, staging, and release commands.
- Never commit signing keys, service credentials, `.env` files, or generated
  dependency directories.
