# Autonomy Levels

> Generated: 2026-06-27
> Based on: ORCHESTRATOR_POLICY.md + ORCHESTRATOR_COMPLETION_PROMPT section 23

## Autonomy Classification

### Level 0: No Autonomy
- Owner-only actions
- Cannot be performed by any profile
- Examples: production deploy, credential rotation, Hetzner resource creation, DNS changes

### Level 1: Inform
- Agent may prepare plans, reports, analysis
- Owner must review and approve before execution
- Examples: architecture ADR, security audit, cost estimate, Terraform plan

### Level 2: Consult
- Agent may execute low-risk actions autonomously
- Must notify owner after completion
- Examples: create feature branch, run tests, update docs, create low-risk PR

### Level 3: Delegate
- Agent may execute defined workflows within guardrails
- Must report results
- Examples: autopilot cron tasks, smoke tests, monitoring checks

### Level 4: Autonomous
- Agent may execute all non-restricted actions without prior approval
- Must report anomalies
- Examples: full development cycle for low-risk features (branch → code → test → PR → merge)

## Profile Autonomy Matrix

| Profile | Max Level | Notes |
| --- | --- | --- |
| default/owner | 4 | Full autonomy within approval boundaries |
| development | 3 | Code + test + PR; no deploy without approval |
| architecture | 1 | Review and design only; no execution |
| research | 2 | Research + notes; no infra changes |
| devops | 2 | Staging bootstrap + monitoring; no production |
| design | 2 | Specs + briefs; no code execution |
| finance | 1 | Read-only reports |
| team | 2 | Task updates; no code execution |

## Guardrails

1. **Budget**: Max 12 tool actions per autopilot cycle
2. **Scope**: One small completed task per cycle
3. **No secrets**: Never read, write, or expose secrets
4. **No production**: No production environment changes
5. **No paid resources**: No cloud resource creation
6. **No destructive actions**: No delete, drop, truncate
7. **No force push**: Never force push any branch
8. **Clean state**: No dirty working tree before/after
9. **Tested**: Every code change must have passing tests
10. **Documented**: Every phase must have updated docs

## Escalation

| Trigger | Action |
| --- | --- |
| High-risk task detected | Stop, classify, prepare approval request |
| Test failure | Stop, report, do not merge |
| Unexpected state | Stop, assess, report |
| Credential needed | Stop, prepare exact secret name + purpose |
| Budget exceeded | Stop, report usage |
| External API failure | Retry once, then report |
