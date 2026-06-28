# Obsidian Vault Setup

> Last updated: 2026-06-27

## Vault Location

- **Path:** `C:\Obsidian\Pulse of Earth` (Windows)
- **Git sync:** via `docs/obsidian/` in this repository

## Initial Setup

### Option A: Git Sync (Recommended)

1. Install **Obsidian Git plugin**:
   - Open Obsidian → Settings → Community plugins → Browse
   - Search "Git" → Install → Enable

2. Clone the repository vault:
   ```bash
   git clone git@github.com:IIIH23/earth-pulse-poc.git
   cd earth-pulse-poc
   # Create .obsidian/ config directory
   ```

3. Configure Git plugin:
   - Pull interval: 5 minutes
   - Auto push on save: ✅
   - Commit message: "vault backup: {{date}}"

### Option B: Direct Vault (No Git)

1. Create new vault in Obsidian: **Open vault** → New vault
2. Path: any writable directory
3. Sync via Syncthing or other file sync

## Required Templates

### ADR (Architecture Decision Record)

Create `Templates/ADR.md`:

```markdown
---
type: adr
status: proposed
date: {{date}}
---

# ADR-XXX: {{title}}

## Context
{{context}}

## Decision
{{decision}}

## Alternatives
{{alternatives}}

## Consequences
{{consequences}}

## Security
{{security}}

## Rollback
{{rollback}}
```

### Weekly Summary

Create `Templates/Weekly Summary.md`:

```markdown
---
type: report
date: {{date}}
---

# Week {{week}} Summary

## Completed
- 

## In Progress
- 

## Blocked
- 

## Next Week
- 

## Metrics
- Deployments: 
- Rollbacks: 
- Open issues: 
```

### Deploy Report

Create `Templates/Deploy Report.md`:

```markdown
---
type: deploy
environment: {{environment}}
status: {{status}}
---

- Environment: {{environment}}
- App: pulse-of-earth
- Commit: {{commit}}
- Tag: {{tag}}
- Actor: Hermes
- Timestamp: {{timestamp}}
- Result: {{result}}
- Rollback: {{rollback}}
```

## Folder Structure

```
Pulse of Earth/
├── 00 Inbox/
├── Agent Logs/
│   ├── Hermes/
│   └── Codex/
├── AI Inbox/
├── Architecture/
├── Decisions/
├── Linear Sync/
├── Templates/
│   ├── ADR.md
│   ├── Discovery.md
│   ├── Deploy Report.md
│   ├── Weekly Summary.md
│   └── ...
└── Daily/
    └── {{date}}.md
```

## Owner Actions

1. Install Obsidian (if not already)
2. Set up Git plugin OR Syncthing
3. Configure vault path
4. Create templates (I can provide content)
