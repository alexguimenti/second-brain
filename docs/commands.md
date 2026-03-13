# Command Reference

## /vault

Search and load files from the Obsidian vault into any Claude Code conversation.

### Modes

| Mode | Usage | Behavior |
|------|-------|----------|
| Keyword search | `/vault <keywords>` | Parallel Grep+Glob, rank by relevance, auto-load top 3 |
| Path load | `/vault --path <folder>` | Load all `.md` files in a vault folder |
| Type filter | `/vault --type <type>` | List files matching a document type |
| Type + search | `/vault --type <type> <keywords>` | Filter by type, then keyword search within |
| Type + path | `/vault --type <type> --path <folder>` | Combine type filter with path load |
| List types | `/vault --types` | Show all types with file counts |
| Help | `/vault` (no args) | Show vault stats and usage |

### Examples

```
/vault reliability plan          # Search for "reliability plan" across all files
/vault --path ClickUp/Product - RB   # Load all Report Builder docs
/vault --type session            # List all session summaries
/vault --type clickup-doc roadmap    # Search "roadmap" in ClickUp docs only
/vault --types                   # Show type breakdown
```

### Search Behavior

1. **Glob** scans all `**/*.md` filenames for keyword matches
2. **Grep** searches file contents with 2 lines of context per match
3. Claude synthesizes both result sets, judging relevance from snippets
4. Top 3 files are auto-loaded into conversation context
5. Remaining matches listed as `[N] title — path` for manual loading

### Output Format

```
## Vault Search: "reliability plan"

### Auto-loaded (3 files):
1. LLMv Platform Reliability Plan
   ClickUp/Product - LLMv/LLMv Platform Reliability Plan.md
2. RB Platform Reliability Plan
   ClickUp/Product - RB/RB Platform Reliability Plan.md
3. ...

### More matches (say "load N" to load):
[4] Alert Strategy — ClickUp/Product - LLMv/...
[5] ...
```

### Context Budget

- Max 3 files auto-loaded per search
- Large files trigger a warning before loading
- Grep output capped at ~200 lines
- Say "load 4, 5" to load additional matches

---

## /sync-clickup

One-way sync of ClickUp documents into the Obsidian vault as markdown with frontmatter.

### Modes

| Mode | Usage | Behavior |
|------|-------|----------|
| Sync all | `/sync-clickup` | Sync every tracked document |
| Sync one | `/sync-clickup <name>` | Sync a single document by name |
| Discover | `/sync-clickup --discover [keywords]` | Search ClickUp for docs to track |
| Add by ID | `/sync-clickup --add <id> <name> <path>` | Add a document to tracking config |
| Add by URL | `/sync-clickup <clickup-url>` | Add a document from its ClickUp URL |

### Configuration

Config file: `<vault_root>/ClickUp/sync-config.json`

```json
{
  "documents": [
    {
      "document_id": "8chy2nm-1234567",
      "name": "My Document",
      "vault_path": "ClickUp/Category/My Document"
    }
  ],
  "defaults": {
    "content_format": "text/md",
    "max_page_depth": -1,
    "flatten": false
  }
}
```

| Field | Description |
|-------|-------------|
| `document_id` | ClickUp document ID (from URL or API) |
| `name` | Display name for the document |
| `vault_path` | Relative path in vault where pages are written |
| `max_page_depth` | How deep to traverse page tree (-1 = unlimited) |
| `flatten` | If true, all pages go into `vault_path/` directly (no hierarchy) |

### Synced File Format

Each ClickUp page becomes a markdown file with frontmatter:

```markdown
---
type: clickup-doc
clickup_doc_id: "8chy2nm-1234567"
clickup_page_id: "page-abc"
title: "Page Title"
last_synced: 2026-03-13T10:30:00Z
source_url: "https://app.clickup.com/..."
parent_page: "Parent Page Title"
---

<page content in markdown>
```

### Error Handling

| Error | Message |
|-------|---------|
| No ClickUp MCP | "ClickUp MCP is not connected. Add it via Claude settings." |
| Document not found | "Document `<id>` not found. It may have been deleted." |
| Empty config | "No documents tracked. Use `--discover` to find docs." |
| Page fetch failure | Logged and skipped; reported in sync summary |

---

## /save-session

Save a structured summary of the current Claude Code session to the vault.

### Usage

```
/save-session                    # Auto-generate title from conversation
/save-session deployment fix     # Use custom title slug
```

### Behavior

1. Scans the full conversation for context, outcomes, decisions, and insights
2. Checks for an existing session note (one session = one note, even across resumes)
3. Discovers related vault notes for wikilinks
4. Writes a structured markdown note to `Claude Code/Sessions/`

Trivial conversations (greetings, quick lookups) are skipped — no empty notes created.

### Output Format

```
## Session Saved

File: Claude Code/Sessions/2026-03-13-deployment-fix.md
Tags: deployment, debugging, infrastructure
Links: [[Previous Session]], [[Related Tool Doc]]
Status: New note created

Resume:
cd "C:\Users\alexg\Documents\Projects\my-project"; claude --resume abc123
```

### Frontmatter Schema

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | Always `session` |
| `date` | date | Session creation date (YYYY-MM-DD) |
| `project` | string | Inferred project name |
| `session_id` | string | Claude session ID |
| `project_path` | string | Windows path to working directory |
| `tags` | list | 3-7 relevant themes |
