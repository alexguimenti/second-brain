Sync active Linear tickets to the Obsidian vault as a status snapshot per team (one-way: Linear → Vault).

## Arguments
`$ARGUMENTS` — optional: a team key (e.g., `rb`, `llmv`, `gsc`) to sync only one team. No args = sync all tracked teams.

## Constants

- Vault root: `{{VAULT_ROOT}}`
- Output: one file per team at `Work/Linear/<TeamKey>.md`
- Teams to sync: `LLMV`, `RB`, `GSC`

## Instructions

### Step 1: Determine scope

From `$ARGUMENTS`:
1. **No arguments** → sync all 3 teams: LLMV, RB, GSC
2. **A team key** (e.g., `llmv`) → sync only that team (case-insensitive)

### Step 2: Fetch tickets from Linear

For each team to sync, use the Linear MCP `list_issues` tool:

```
list_issues(teamId: "<team_key>", limit: 100, statuses: ["In Progress", "In Review", "Ready for Dev", "Todo", "Blocked"])
```

This fetches only **active** tickets — not Done, Cancelled, or Backlog.

If `list_issues` doesn't support filtering by status, fetch all open tickets and filter client-side.

### Step 3: Write snapshot file

For each team, write **one file** that is overwritten on every sync:

**File path:** `{{VAULT_ROOT}}/Work/Linear/<TeamKey>.md`

Example: `Work/Linear/LLMV.md`

**Content:**

```markdown
---
type: linear-snapshot
team: <LLMV>
last_synced: <current ISO 8601 timestamp>
total_active: <count>
---

# Linear — <TeamKey>

*Last synced: <YYYY-MM-DD HH:MM>*

## In Progress (<count>)

| Ticket | Title | Priority | Assignee |
|--------|-------|----------|----------|
| [<ID>](<url>) | <title truncated to 60 chars> | <priority> | <assignee> |
| ... | ... | ... | ... |

## In Review (<count>)

| Ticket | Title | Priority | Assignee |
|--------|-------|----------|----------|
| ... | ... | ... | ... |

## Ready for Dev (<count>)

| Ticket | Title | Priority | Assignee |
|--------|-------|----------|----------|
| ... | ... | ... | ... |

## Todo (<count>)

| Ticket | Title | Priority | Assignee |
|--------|-------|----------|----------|
| ... | ... | ... | ... |

## Blocked (<count>)

| Ticket | Title | Priority | Assignee |
|--------|-------|----------|----------|
| ... | ... | ... | ... |
```

**Rules:**
- **Always overwrite** the entire file — this is a snapshot, not a log
- Skip empty status sections (don't show "In Review (0)" if there are none)
- Sort tickets within each section by priority (Urgent first, then High, Medium, Low)
- Truncate ticket titles to 60 characters in the table
- Ticket ID should be a markdown link to the Linear URL
- Create `Work/Linear/` directory if it doesn't exist

### Step 4: Summary report

```
## Linear Sync Complete

| Team | Active Tickets | File |
|------|---------------|------|
| LLMV | <N> | Work/Linear/LLMV.md |
| RB | <N> | Work/Linear/RB.md |
| GSC | <N> | Work/Linear/GSC.md |

*Next automatic sync: <08:00 or 14:00>*
```

## Error Handling

- **Linear MCP not connected:** "Linear MCP is not connected. Check your Claude Code settings."
- **Team not found:** "Team '<key>' not found. Available teams: LLMV, RB, GSC."
- **No active tickets:** Write the file with "No active tickets" under a single section.
