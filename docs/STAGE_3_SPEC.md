# Stage 3 — Hermes-Obsidian Sync Specification

> Created: 2026-06-28T13:30:00Z
> Status: DRAFT — ready for owner review

## Scope

Define how Hermes project memory (ROADMAP.md, AUTOPILOT_STATE.md, AUTOPILOT_LOG.md) and
autopilot outputs sync with an Obsidian vault used by humans on Windows.

## Design Decision

**Sync direction: ONE-WAY (Git → Obsidian)**

Hermes is the authoritative source for project-state files. Obsidian is the read/view
surface for humans. Human edits in Obsidian are informational only and do not flow back
into autopilot logic.

```
Hermes (autopilot) → Git repo (docs/obsidian/) → Git plugin pull → Obsidian vault (read/view)
Obsidian human edits → Git plugin push → Git repo → manual review only (ignored by autopilot)
```

**Rationale:**
- Prevents race conditions and concurrent-edit conflicts while autopilot runs on schedule.
- Keeps autopilot writes deterministic — it only writes from a known state, never from
  unstructured user edits.
- Humans can still add notes in Obsidian; they just don't affect autopilot behavior.

## Conflict Behavior

| Scenario | Resolution |
|---|---|
| Hermes writes `docs/obsidian/STATE.md` while human edits same file in Obsidian | Hermes wins on next push. Human edits must be rebased manually. |
| Obsidian Git plugin has unpulled changes when Hermes pushes | Push fails → autopilot logs error, retries next cycle. Human must pull first. |
| Both sides modify different files | No conflict. Both changes coexist. |

## Note Naming Convention

All Hermes-managed notes live under `docs/obsidian/` and follow this naming:

```
docs/obsidian/
├── STATE.md              ← mirror of AUTOPILOT_STATE.md
├── ROADMAP.md            ← mirror of ROADMAP.md
├── LOG-<YYYY-MM-DD>.md   ← daily autopilot log entries
└── DECISIONS/
    └── ADR-XXX-<slug>.md ← architecture decision records
```

- Daily log: `LOG-2026-06-28.md` (one file per UTC day).
- ADRs: `ADR-001-use-git-sync.md`, `ADR-002-one-way-sync.md`, etc.
- All files are valid Obsidian Markdown (YAML frontmatter optional).

## Sync Script (planned for Stage 3 implementation)

A future `tools/obsidian_sync.py` will:

1. Read canonical state files from repo root (`AUTOPILOT_STATE.md`, `ROADMAP.md`).
2. Read today's log entry from `logs/AUTOPILOT_LOG.md`.
3. Write/update corresponding files in `docs/obsidian/`.
4. Run `git add docs/obsidian/ && git commit -m "obsidian sync: <timestamp>"`.

This script is NOT yet implemented — it is the first deliverable of Stage 3.

## Owner Actions Required

1. Install Obsidian Git plugin (or Syncthing) on Windows vault.
2. Configure vault to track `docs/obsidian/` from this repository.
3. Confirm vault path (currently assumed `C:\Obsidian\Pulse of Earth`).

## Out of Scope (Stage 3)

- Two-way sync (human edits → autopilot state).
- Real-time sync (webhook-based).
- Obsidian MCP server integration.
- Mobile Obsidian support.
