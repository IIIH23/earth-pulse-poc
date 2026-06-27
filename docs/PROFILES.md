# Hermes Profiles

> Generated: 2026-06-27
> Based on: ORCHESTRATOR_COMPLETION_PROMPT section 4

## Profile Overview

| Profile | Model | Fallback | Primary Use |
| --- | --- | --- | --- |
| default (owner) | openrouter/owl-alpha | openrouter/owl-alpha | Orchestration, strategy, approvals, reports |
| development | openrouter/owl-alpha | openrouter/owl-alpha | Coding, tests, CI/CD, staging deploy |
| architecture | openrouter/owl-alpha | openrouter/owl-alpha | ADR, security, system design |
| research | openrouter/owl-alpha | openrouter/owl-alpha | Analysis, knowledge notes |
| devops | openrouter/owl-alpha | openrouter/owl-alpha | Infrastructure, monitoring, backups |
| design | openrouter/owl-alpha | openrouter/owl-alpha | UX specs, design briefs |
| finance | openrouter/owl-alpha | openrouter/owl-alpha | Budgets, cost estimates |
| team | openrouter/owl-alpha | openrouter/owl-alpha | Task tracking, Linear sync |

## Profile Permissions

### default (owner)
- **Tools**: all
- **Secrets**: read/write (with approval)
- **Actions**: all (with approval for high-risk)
- **Approval role**: approves requests from other profiles

### development
- **Tools**: terminal, file, web, browser, coding, github, search
- **Secrets**: none (uses deploy keys, CI secrets via GitHub Actions)
- **Actions**: branch, commit, test, PR, staging deploy
- **Forbidden**: production deploy, secrets modify, firewall, DNS

### architecture
- **Tools**: terminal, file, web, search, coding (read-only review)
- **Secrets**: none
- **Actions**: ADR, design review, security review
- **Forbidden**: deploy, secrets modify, infra changes

### research
- **Tools**: terminal, file, web, search, x_search
- **Secrets**: none
- **Actions**: research, analysis, documentation
- **Forbidden**: code changes, deploy, infra

### devops
- **Tools**: terminal, file, web, coding, github
- **Secrets**: none (uses deploy keys)
- **Actions**: bootstrap, monitoring, backup, restore, staging deploy
- **Forbidden**: production deploy, DNS, firewall, secrets modify

### design
- **Tools**: terminal, file, image_gen, web
- **Secrets**: none
- **Actions**: specs, briefs, design handoff
- **Forbidden**: code, deploy, infra

### finance
- **Tools**: terminal, file, web
- **Secrets**: none (read-only cost data)
- **Actions**: reports, estimates, budgets
- **Forbidden**: all write actions, deploy, infra

### team
- **Tools**: terminal, file, web, search
- **Secrets**: none
- **Actions**: task updates, Linear sync, reports
- **Forbidden**: code, deploy, secrets

## Escalation Path

```
Profile needs high-risk action
  → Stop and prepare approval request
  → Send to owner via Telegram
  → Owner approves/rejects
  → If approved, execute with safeguards
```

## Implementation Notes

- Profiles are logical separations documented here; Hermes profile system may need configuration in `~/.hermes/profiles/`.
- Each profile should have its own workspace, skills, and memory.
- Owner profile is the only one that can approve high-risk actions.
