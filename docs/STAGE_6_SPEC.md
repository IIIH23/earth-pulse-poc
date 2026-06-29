# Stage 6: GitHub Sync — Specification

> Status: ✅ complete
> Created: 2026-06-29
> Completed: 2026-06-29
> Owner: Hermes autopilot

## Objective

Define which Pulse of Earth artifacts are mirrored to GitHub, establish sync
direction and manual-approval boundaries, and implement a lightweight sync
checker that reports drift between local state and GitHub.

## Current state

- Remote already configured: `git@github.com:IIIH23/earth-pulse-poc.git`
- CI workflow exists (`.github/workflows/ci.yml`) with lint/test/security jobs.
- GitHub Environments doc exists (`docs/GITHUB_ENVIRONMENTS.md`) — describes
  staging/production deployment flow but NOT repository sync scope.
- No tooling exists to verify or report sync state between local and remote.

## Sync scope

### Auto-synced (pushed to GitHub on every local commit)

| Artifact | Path | Rationale |
| --- | --- | --- |
| Application code | `tools/`, `src/` | Core logic belongs in VCS |
| Tests | `tests/` | CI runs them |
| CI workflows | `.github/workflows/` | CI/CD config |
| Docs | `docs/` | Project documentation |
| Roadmap & state | `ROADMAP.md`, `AUTOPILOT_STATE.md`, `AUTOPILOT_LOG.md` | Project coordination |
| Config | `requirements*.txt`, `Dockerfile`, `compose.yaml`, `configs/` | Reproducibility |
| Scripts | `scripts/` | Operational tooling |

### NOT synced (local-only, listed in .gitignore or outside scope)

| Artifact | Reason |
| --- | --- |
| `.env`, secrets | Security — never commit secrets |
| `.venv/`, `.venv_autopilot/` | Local virtual environments |
| `automation-bootstrap.log` | Large operational log (223 KB), not project code |
| `*.local.md` drafts | Work-in-progress notes |
| `decisions/` | Internal decision records (may contain sensitive context) |

### Manual-approval boundary

The following require explicit human approval before pushing:

1. Any change to `.github/workflows/` — CI changes affect deployment
2. Any change to `docs/GITHUB_ENVIRONMENTS.md` — deployment environment config
3. Any change touching `configs/` — may contain deployment parameters
4. Any merge to default branch that isn't a fast-forward from autopilot

## Sync direction

- **Primary**: Local → GitHub (autopilot commits locally, pushes are manual)
- **Secondary**: GitHub → Local (human may open PRs; autopilot does not pull-request)
- **No bidirectional auto-sync**: Obsidian and Linear have their own sync tools

## Deliverables

1. `docs/STAGE_6_SPEC.md` — this document
2. `tools/github_sync.py` — sync checker (stdlib-only CLI):
   - `check` command: compare local HEAD with remote tracking branch
   - Reports: ahead count, behind count, untracked files, uncommitted changes
   - Exit 0 if in sync, exit 1 if drift detected, exit 2 on error
   - `--json` flag for machine-readable output
   - `--dry-run` flag (no network calls, just local state)
3. `tests/test_github_sync.py` — pytest tests for the sync checker

## Verification

- `python3 -m pytest tests/test_github_sync.py -q` — all tests green
- `python3 tools/github_sync.py check --dry-run` — reports local state
- Full suite still green after changes

## Out of scope (future stages)

- Auto-push from autopilot (requires human approval workflow)
- GitHub Issues automation (separate integration)
- Branch protection API calls (requires human GH Pro or public repo)
- GitHub Actions runner on staging VPS
