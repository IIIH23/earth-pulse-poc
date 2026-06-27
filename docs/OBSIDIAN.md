# Obsidian Integration

> Last updated: 2026-06-27

## Vault

- **Path**: `C:\Obsidian\Pulse of Earth` (Windows) or `/home/user/Obsidian/Pulse of Earth` (Linux/Mac)
- **URI**: `obsidian://vault/Pulse%20of%20Earth`

## Vault Structure

```
Pulse of Earth/
├── 00 Inbox/
│   └── (quick capture)
├── Agent Logs/
│   ├── Hermes/
│   │   ├── 2026-06-27.md
│   │   └── ...
│   └── Codex/
├── AI Inbox/
│   └── (AI-generated ideas)
├── Architecture/
│   ├── ADR-001-github-actions.md
│   └── ADR-002-staging-lockdown.md
├── Decisions/
│   └── (decision notes)
├── Linear Sync/
│   └── (issue summaries)
├── Templates/
│   ├── ADR.md
│   ├── Discovery.md
│   ├── MVP Plan.md
│   ├── Incident Report.md
│   ├── Deployment Report.md
│   ├── Weekly Summary.md
│   ├── Research Note.md
│   └── Decision Log.md
└── Daily/
    └── 2026-06-27.md
```

## Templates

### ADR (Architecture Decision Record)

```markdown
# ADR-XXX: Title

## Context
(What is the context?)

## Decision
(What did we decide?)

## Alternatives
(What else was considered?)

## Consequences
(What are the consequences?)

## Security
(Security implications)

## Rollback
(How to reverse?)

## Status
Accepted / Proposed / Deprecated
```

### Discovery

```markdown
## Idea
(One-line description)

## Problem
(What problem does this solve?)

## Target User
(Who benefits?)

## Value
(What value does it provide?)

## Competitors
(What alternatives exist?)

## Constraints
(Limitations)

## Data Sources
(Where does data come from?)

## Legal/Privacy
(Risks)

## Security
(Risks)

## Budget
(Estimated cost)

## Success Metrics
(How to measure success?)

## Non-Goals
(What is out of scope?)

## MVP Scope
(Minimum viable product)

## Technical Outline
(High-level technical approach)

## Risk Review
(Initial risk classification)
```

### Deployment Report

```markdown
## Deployment Report

- **Environment**: staging / production
- **App**: pulse-of-earth
- **Commit**: {{sha}}
- **Tag**: {{tag}}
- **Actor**: Hermes (autopilot)
- **Timestamp**: {{timestamp}}
- **Result**: success / failure
- **Health Check**: pass / fail
- **Rollback**: no / yes (reason)
```

### Weekly Summary

```markdown
# Week {{week}} Summary ({{date_range}})

## Completed
- (list)

## In Progress
- (list)

## Blocked
- (list)

## Next Week
- (list)

## Metrics
- Deployments: X
- Rollbacks: X
- Test coverage: X%
- Open issues: X
```

## Sync Architecture

### Option A: Git Sync (recommended)

```
Hermes → Git repo (docs/obsidian/) → Obsidian Git plugin → Vault
Obsidian → Git plugin → Git repo → Hermes reads
```

- Pros: version control, backup, cross-platform
- Cons: requires Git plugin on Obsidian side

### Option B: File Share / Syncthing

```
Hermes → /shared/obsidian/ → Syncthing → Vault
```

- Pros: real-time, no plugin needed
- Cons: conflict potential, requires Syncthing setup

### Option C: n8n Webhook (future)

```
Hermes → n8n webhook → Obsidian API → Vault
```

- Pros: flexible, automatable
- Cons: requires Obsidian API plugin, n8n setup

## Current Limitation

- Hermes VPS (Linux) cannot directly access Windows Obsidian vault
- No MCP server for Obsidian available
- **Recommended**: Git sync via `docs/obsidian/` directory in repo

## Hermes → Obsidian Flow

1. Hermes creates note in `docs/obsidian/` (Git)
2. Obsidian Git plugin pulls changes
3. Note appears in vault
4. User edits in Obsidian
5. Git plugin pushes changes
6. Hermes reads updated content

## Owner Actions Required

1. Install Obsidian Git plugin (or Syncthing)
2. Configure sync with repository
3. Provide vault path for local development
