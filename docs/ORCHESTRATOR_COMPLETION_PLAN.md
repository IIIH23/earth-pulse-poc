# Orchestrator Completion Plan

> Generated: 2026-06-27
> Branch: feat/orchestrator-phase0
> Based on: ORCHESTRATOR_COMPLETION_PROMPT.md + ORCHESTRATOR_POLICY.md + repository inventory

## Current State Summary

### Done
- Repository initialized (AGENTS.md, ROADMAP.md, ORCHESTRATOR_POLICY.md)
- Staging VPS bootstrapped (Docker, UFW, Fail2ban, swap, deploy user)
- SSH lockdown applied (PermitRootLogin no, PasswordAuthentication no, AllowUsers deploy)
- Smoke tests passing (13 staging tests, 4 lockdown tests, inventory tests)
- Autopilot cron running (every 120m, Telegram delivery)
- Tools: inventory.py implemented with tests
- Skill bundles defined (dev-core, devops-core, design-core, research-core)

### Partially Done
- GitHub integration (no remote configured, no branch protection, no CI beyond smoke.yml)
- Profiles documented in ORCHESTRATOR_COMPLETION_PROMPT but not yet created as Hermes profiles
- Linear integration (not started)
- Obsidian integration (not started)
- n8n architecture (not started)
- Monitoring scripts (not started)
- Security docs (not started)

### Not Started
- Hermes profile creation (default, development, architecture, research, devops, design, team, finance)
- GitHub Actions CI pipeline (lint → test → build → scan → sign → deploy)
- GHCR registry setup
- Caddy reverse proxy on staging
- PostgreSQL container + backups
- Telegram notification module
- Linear sync
- Obsidian sync
- n8n workflows
- Threat model / security audit
- Disaster recovery / runbook

## Phase Plan

| Phase | Name | Status | Effort | Risk |
| --- | --- | --- | --- | --- |
| 0 | Inventory | ✅ done | S | low |
| 1 | Core orchestration (profiles, routing, skills) | ⏳ pending | M | low |
| 2 | GitHub (branch protection, CI, GHCR) | ⏳ pending | M | low |
| 3 | Staging platform (Caddy, compose, health) | ⏳ pending | M | medium |
| 4 | Cloudflare (DNS, Access) | ⏳ pending | S | medium |
| 5 | Linear integration | ⏳ pending | S | low |
| 6 | Obsidian sync | ⏳ pending | S | low |
| 7 | n8n architecture | ⏳ pending | S | low |
| 8 | Backups and monitoring | ⏳ pending | M | medium |
| 9 | Security review | ⏳ pending | M | medium |
| 10 | Final acceptance | ⏳ pending | S | low |

## Blockers

1. **No GitHub remote configured** — cannot push or create PRs without `git remote add`.
2. **No GitHub admin credentials** — branch protection, environments, and secrets require owner action.
3. **No Cloudflare API token** — DNS records and Access policies require owner-provided token.
4. **No Linear API key** — task sync requires owner-provided key.
5. **No Hetzner Object Storage** — PostgreSQL backups require owner-provisioned bucket.
6. **No Docker Hub / GHCR auth** — image pulls require credentials.
7. **Cron model drift** — pulse-autopilot cron is paused due to provider/model change; needs `cronjob update` with explicit provider/model pin.

## Credentials Required

| Credential | Purpose | Owner Action |
| --- | --- | --- |
| GitHub PAT | repo create, branch protection, CI | Required |
| GitHub Environment secrets | staging/production deploy | Required |
| Cloudflare API token | DNS, Access | Required |
| Linear API key | task sync | Required |
| Hetzner Cloud API | VPS management, Terraform | Required |
| Hetzner Object Storage | PostgreSQL backups | Required |
| Telegram Bot token | alerts | Required |
| Docker Hub / GHCR auth | image pull | Required |

## Approvals Required

1. GitHub remote + branch protection (owner)
2. Cloudflare DNS record creation (owner)
3. Linear project setup (owner)
4. Hetzner resource creation (Terraform apply) (owner)
5. Production deployment (owner)
6. Credential rotation (owner)

## Next Steps

1. Pin cron to current provider/model (low-risk, immediate)
2. Create Hermes profiles (low-risk)
3. Create GitHub remote + branch protection plan (needs owner)
4. Implement reusable CI workflow (low-risk, local only)
