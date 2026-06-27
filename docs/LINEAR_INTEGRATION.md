# Linear Integration

> Last updated: 2026-06-27

## Setup

- **Workspace**: TerraBits
- **Team**: Engineering
- **Project**: Pulse of Earth
- **API key**: stored in GitHub Environment as `LINEAR_API_KEY`

## Project Structure

```
Pulse of Earth (project)
├── Discovery (initiative)
├── Architecture (initiative)
├── Development (initiative)
└── Operations (initiative)
```

## Issue Lifecycle

```
Todo → In Progress → In Review → Done
                            ↘ Cancelled
```

## Labels

| Label | Color | Purpose |
| --- | --- | --- |
| discovery | blue | Discovery tasks |
| architecture | purple | ADR, design |
| backend | green | Server-side |
| frontend | yellow | UI |
| devops | orange | Infra, CI/CD |
| security | red | Security |
| testing | gray | Test tasks |
| documentation | teal | Docs |
| low-risk | green dot | Auto-merge eligible |
| medium-risk | yellow dot | Needs 1 reviewer |
| high-risk | red dot | Needs 2 reviewers + owner |
| blocked | black | Waiting on dependency |
| needs-owner | white | Owner decision required |

## Priority

| Priority | Value |
| --- | --- |
| 0 | Urgent |
| 1 | High |
| 2 | Medium |
| 3 | Low |
| 4 | No priority |

## States

| State | Purpose |
| --- | --- |
| Todo | Not started |
| In Progress | Active work |
| In Review | PR open |
| Done | Merged/deployed |
| Cancelled | Won't do |

## Mapping to ROADMAP.md

| Roadmap Stage | Linear Initiative | Labels |
| --- | --- | --- |
| 1. Audit | Discovery | discovery |
| 2. Port Logic | Development | backend |
| 3. Hermes-Obsidian | Architecture | architecture |
| 4. Hermes-Linear | Architecture | architecture |
| 5. n8n Workflows | Development | backend, devops |
| 6. GitHub Sync | Operations | devops |
| 7. Tests | Development | testing |
| 8. Docs & Backup | Operations | documentation, devops |
| 9. Partner Profile | Discovery | discovery |

## Sync Rules

1. Create Linear issue when discovery is approved
2. Update status after commit/PR/deploy
3. Add PR link to issue
4. Add test results to issue
5. Do not close high-risk issues without owner approval
6. Do not duplicate issues on re-sync

## Idempotency

- Before creating issue, search for existing by title+project
- If exists, update status instead of creating duplicate
- Use external ID (commit SHA) to track sync state

## Dry-Run Mode

- `--dry-run` flag: log what would be created/updated without making API calls
- Useful for verifying mapping before first sync

## Owner Actions Required

1. Create Linear workspace (if not exists)
2. Create Pulse of Earth project
3. Provide API key
4. Create labels and states as listed above
