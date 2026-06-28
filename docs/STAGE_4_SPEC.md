# Stage 4: Hermes–Linear synchronization specification

## Scope

Stage 4 mirrors every numbered stage in `ROADMAP.md` to one issue in the
Pulse of Earth Linear project. The repository remains the source of truth.
Linear is a planning and status view; edits made only in Linear are overwritten
on the next sync.

The API endpoint is `https://api.linear.app/graphql`. Requests are JSON `POST`
requests with `Content-Type: application/json` and
`Authorization: Bearer <token>`. The token comes from `LINEAR_API_KEY`, unless
the CLI receives `--api-key`.

The client sends at most one request per two seconds. This is deliberately
stricter than Linear's published search limit and applies to searches,
creates, updates, and retries.

## GraphQL operations

Linear issues require a team, although the CLI is configured with a project.
`withIssueSearch` therefore returns the project's teams, states, labels, and
initiatives together with matching issues. The first project team is used.
The Pulse of Earth project is expected to have exactly one team.

Linear currently marks `issueSearch` as deprecated in favor of `searchIssues`.
Stage 4 uses `issueSearch` because this operation is part of the requested
contract. A later migration can change the field to `searchIssues` without
changing the idempotency marker.

```graphql
query withIssueSearch($query: String!, $projectId: String!) {
  issueSearch(query: $query, first: 20, includeArchived: false) {
    nodes {
      id
      identifier
      title
      description
      project { id }
    }
  }
  project(id: $projectId) {
    id
    teams(first: 10) {
      nodes {
        id
        states(first: 50) { nodes { id name } }
        labels(first: 100) { nodes { id name } }
      }
    }
    initiatives(first: 50) { nodes { id name } }
  }
}
```

The client searches for the deterministic external ID, then requires an exact
external-ID marker and project match in the returned issue. Search results that
only happen to contain similar text are ignored.

```graphql
mutation createIssue($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue { id identifier title }
  }
}
```

The create input contains `teamId`, `projectId`, `title`, `description`,
`priority`, `stateId`, and `labelIds`.

```graphql
mutation updateIssue($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue { id identifier title }
  }
}
```

The update input contains `projectId`, `title`, `description`, `priority`,
`stateId`, and `labelIds`. GraphQL responses with an `errors` array or a false
mutation `success` value are failures even when HTTP status is 200.

## Roadmap parsing and field mapping

Only level-two headings matching `## N. StageName` are stages. Each stage
continues until the next level-two heading. The recognized bullets are
`Objectives`, `Success criteria`, `Estimated effort`, and `Status`. A missing
status means `Not started`.

| ROADMAP.md value | Linear issue field |
| --- | --- |
| Heading number and name | `title`: `Stage N: StageName` |
| Objectives, success criteria, effort, status | Markdown `description` |
| Status containing `done` | workflow state `Done` |
| Any other or missing status | workflow state `Todo` |
| Effort `L` | priority `2` (High) |
| Effort `M` | priority `3` (Medium) |
| Effort `S` | priority `4` (Low) |
| Unknown effort | priority `0` (No priority) |
| Stage mapping below | issue `labelIds`, resolved by label name |
| `--project-id` | issue `projectId` |
| Initiative mapping below | indirect through the selected project; recorded in description |

Linear has no issue-to-initiative field. Initiatives group projects, so the
configured project must be associated with the named initiatives. The sync
does not attempt to move the shared project between initiatives for each
issue.

| Stage | Label(s) | Initiative |
| --- | --- | --- |
| 1 Audit | `discovery` | Discovery |
| 2 Port Logic | `backend` | Development |
| 3 Hermes-Obsidian | `architecture` | Architecture |
| 4 Hermes-Linear | `architecture` | Architecture |
| 5 Deterministic Workflows With n8n | `backend`, `devops` | Development |
| 6 GitHub Sync | `devops` | Operations |
| 7 Tests & Smoke-Tests | `testing` | Development |
| 8 Docs & Backup/Restore | `documentation`, `devops` | Operations |
| 9 Partner Profile | `discovery` | Discovery |
| Other stages | `documentation` | Operations |

The required labels and `Todo`/`Done` workflow states must already exist.
Missing configured fields stop the sync rather than silently producing
incorrectly classified issues.

## Description template

```markdown
<!-- pulse-of-earth-external-id: pulse-of-earth-stage-N -->

## Objective

<Objectives value, or "Not specified.">

## Success criteria

<Success criteria value, or "Not specified.">

## Estimated effort

<Estimated effort value, or "Not specified.">

## Status

<Status value, or "Not started">

## Planning metadata

- Roadmap stage: N
- Initiative: <mapped initiative>
- External ID: `pulse-of-earth-stage-N`
```

## Idempotency and state

The deterministic external ID is `pulse-of-earth-stage-N`. Linear's
`IssueCreateInput` has no external-ID field, so the value is stored in an HTML
comment and in visible planning metadata. Before every create, the client
searches for this value and verifies the exact marker. A match is updated,
never recreated.

The local state file defaults to `.linear-sync-state.json` and has this shape:

```json
{
  "4": {
    "issue_id": "Linear UUID",
    "issue_identifier": "ENG-123",
    "last_sync_hash": "sha256 of the canonical logical payload"
  }
}
```

The file is written atomically only after a successful non-dry-run sync.
Deleting it does not create duplicates because remote search is authoritative.

## Failure handling

- Missing API key: fail before making a request, print a JSON error to stdout,
  and exit 1. This is the local equivalent of avoiding a 401.
- HTTP 401: do not retry. Report that `LINEAR_API_KEY` is missing or invalid,
  never print the token, and exit 1.
- HTTP 429: honor an integer `Retry-After` header when present, otherwise wait
  two seconds. Retry at most three total attempts, still respecting the
  two-second request interval.
- Network errors: wait two seconds and retry at most three total attempts.
  After the final failure, report a concise error and exit 1.
- Other HTTP errors, invalid JSON, GraphQL errors, missing required project
  metadata, or unsuccessful mutations: fail without writing the state file.

`--dry-run` requires neither an API key nor a project ID. It parses and maps the
roadmap, prints a JSON plan, makes no HTTP calls, and does not write state.
Actual synchronization requires `--project-id`.
