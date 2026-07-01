# AI Orchestrator Integration

## Boundary

Pulse of Earth and AI Orchestrator are separate systems with an explicit
integration.

Pulse of Earth owns:

- live seismic acquisition and signal processing;
- the 26-second detector and collection scripts;
- the public `earth-pulse.json` schema and data;
- the scheduled feed-publication workflow;
- product-facing breathing-rhythm interpretation.

AI Orchestrator owns:

- agent routing and approval policy;
- GitHub, Linear, Obsidian, and Telegram adapters;
- verification evidence, reporting, and audit trails;
- reusable staging, monitoring, and rollback patterns.

## Current infrastructure fit

The Orchestrator is useful as a control plane for repository checks, pull
requests, workflow observation, roadmap synchronization, and operational
notifications.

It is not part of the current application runtime. Pulse of Earth publishes a
static JSON feed through GitHub Actions and does not currently need the
Orchestrator's Docker, PostgreSQL, Caddy, Cloudflare, or n8n prototypes.

If a future API or stateful backend is introduced, those components must be
evaluated and implemented as deployable infrastructure before adoption.

## Contract

`orchestrator-project.yaml` declares the repository, branch, public artifact,
workflows, allowed automation, and owner-approval boundaries. The matching
control-plane profile lives in the AI Orchestrator repository at
`projects/pulse-of-earth.yaml`.
