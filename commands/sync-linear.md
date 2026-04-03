Sync active Linear tickets to the Obsidian vault as Markdown files (one-way: Linear → Vault).

## Arguments
`$ARGUMENTS` — optional: a team key (e.g., `rb`, `llmv`, `gsc`) to sync only one team. No args = sync all tracked teams.

## Constants

- Vault root: `{{VAULT_ROOT}}`
- Output path: `Work/Linear/<TeamKey>/`
- Teams to sync: `LLMV`, `RB`, `GSC`

## Instructions

### Step 1: Determine scope

From `$ARGUMENTS`:
1. **No arguments** → sync all 3 teams: LLMV, RB, GSC
2. **A team key** (e.g., `llmv`) → sync only that team (case-insensitive)

### Step 2: Fetch tickets from Linear

For each team to sync, use the Linear MCP `list_issues` tool:

```
list_issues(teamId: "<team_key>", limit: 50, statuses: ["In Progress", "In Review", "Ready for Dev", "Todo", "Blocked"])
```

This fetches only **active** tickets — not Done, Cancelled, or Backlog.

If `list_issues` doesn't support filtering by status, fetch all open tickets and filter client-side.

### Step 3: Write tickets to vault

For each ticket, write a markdown file:

**File path:** `{{VAULT_ROOT}}/Work/Linear/<TeamKey>/<identifier>.md`

Example: `Work/Linear/LLMV/LLMV-288.md`

**Content:**

```markdown
---
type: linear-ticket
identifier: <LLMV-288>
title: "<ticket title>"
status: <In Progress>
priority: <priority name>
assignee: <assignee name or Unassigned>
labels: [<label1>, <label2>]
created: <YYYY-MM-DD>
updated: <YYYY-MM-DD>
last_synced: <current ISO 8601 timestamp>
url: "<linear URL>"
---

# <identifier>: <title>

## Description

<ticket description in markdown>

## Metadata

- **Status:** <status>
- **Priority:** <priority>
- **Assignee:** <assignee>
- **Labels:** <labels joined by comma>
- **Created:** <date>
- **Updated:** <date>
```

**Rules:**
- Always overwrite existing files — no change detection
- Create directories as needed (`mkdir -p`)
- Sanitize filenames: strip `< > : " / \ | ? *` from ticket identifiers (shouldn't be needed for Linear IDs like LLMV-288)

### Step 4: Clean up resolved tickets

After writing active tickets, check for `.md` files in the team folder that don't match any active ticket identifier. These are tickets that moved to Done/Cancelled since the last sync.

**Do NOT delete them.** Instead, read the file, check if the frontmatter status differs from the current status, and update the status to the current one (e.g., "Done"). This way the vault keeps a record of completed tickets but with accurate status.

### Step 5: Summary report

```
## Linear Sync Complete

| Team | Active | Updated | Total in vault |
|------|--------|---------|----------------|
| LLMV | <N> | <N changed> | <N files> |
| RB | <N> | <N changed> | <N files> |
| GSC | <N> | <N changed> | <N files> |

**Total:** <N> active tickets synced
```

## Error Handling

- **Linear MCP not connected:** "Linear MCP is not connected. Check your Claude Code settings."
- **Team not found:** "Team '<key>' not found. Available teams: LLMV, RB, GSC."
- **No active tickets:** Report 0 active tickets for that team — still valid, nothing to write.
