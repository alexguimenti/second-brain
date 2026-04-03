# Command Reference

## /vault

Search and load files from the Obsidian vault into any Claude Code conversation.

### Modes

| Mode | Usage | Behavior |
|------|-------|----------|
| Keyword search | `/vault <keywords>` | Parallel Grep+Glob, rank by relevance, show summaries |
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

`/vault` supports two search backends, selected automatically:

#### QMD Backend (preferred)

When the QMD MCP server is registered, `/vault` uses hybrid search:

1. **BM25 full-text search** — fast keyword matching with phrase support
2. **Vector semantic search** — meaning-based retrieval using local embeddings
3. **HyDE** — generates a hypothetical answer document and finds similar real docs
4. **LLM re-ranking** — Qwen3 reranks top results for final ordering

A single `query()` call to QMD runs all four methods and returns fused, ranked results with snippets.

**Semantic matching examples:**
- "payment failures" finds docs about "billing retry", "credit card errors", "charge disputes"
- "deploy strategy" finds docs about "rollback procedures", "canary releases", "feature flags"

#### Grep/Glob Backend (fallback)

When QMD is not available, `/vault` falls back to keyword search:

1. **Glob** scans all `**/*.md` filenames for keyword matches
2. **Grep** searches file contents with 2 lines of context per match
3. Claude synthesizes both result sets, judging relevance from snippets

Both backends produce identical output format (summary cards). The user experience is the same — only search quality differs.

### Output Format

```
## Vault Search: "reliability plan"

[1] LLMv Platform Reliability Plan
    ClickUp/Product - LLMv/LLMv Platform Reliability Plan.md
    → 4-week plan covering monitoring, alerting, and failover.
      Key sections: SLA targets, alert layers, rollback procedures.

[2] RB Platform Reliability Plan
    ClickUp/Product - RB/RB Platform Reliability Plan.md
    → Reliability roadmap for Report Builder. Focuses on error handling,
      retry logic, and cache invalidation strategy.

[3] Alert Strategy
    ClickUp/Product - LLMv/Alert Strategy.md
    → Deep dive on P0/P1/P2 alert tiers with escalation policies.

Say "load 1,3" to bring full documents into context.
```

### Context Budget

- **No auto-loading** — summaries cost ~200-300 tokens vs ~5000-10000 for full documents
- User controls exactly which files enter the context window
- Large files trigger a warning before loading
- Grep output capped at ~200 lines
- Up to 10 summary cards per search

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
      "document_id": "your-doc-id-here",
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
clickup_doc_id: "your-doc-id-here"
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
cd "C:\Users\username\Projects\my-project"; claude --resume abc123
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

### Session Auto-Backup

In addition to manual `/save-session`, every non-trivial session is automatically backed up to `Work/Claude Code/Sessions/auto/` via a SessionEnd hook. These notes have type `session-auto` and contain user messages only (no Claude responses).

```
/vault --type session-auto           # List all auto-backups
/vault --type session-auto deploy    # Search "deploy" in auto-backups only
```

### Closing a Session

| Action | What happens |
|--------|-------------|
| `Ctrl+C` or `/exit` | Auto-backup saves lightweight note |
| `/end-session` then `Ctrl+C` | Full save: /log + /save-session + auto-backup |
| Close window (X) | Nothing saved |

---

## /link-vault

Discover and create Obsidian wikilinks between vault files. Finds both inline mentions and semantic relationships.

### Modes

| Mode | Usage | Behavior |
|------|-------|----------|
| Full scan + confirm | `/link-vault` | Scan entire vault, show report, ask before applying |
| Dry run | `/link-vault --dry-run` | Show report only, no changes |
| Auto apply | `/link-vault --auto` | Scan and apply without confirmation |
| Folder scope | `/link-vault --path <folder>` | Scope to a specific folder |
| Single file | `/link-vault <file.md>` | Scope to one file |

Flags combine freely: `/link-vault --path ClickUp/ --dry-run`

### Link Types

**Inline links** — when a file's text mentions another vault file by name, the mention is wrapped in `[[wikilinks]]`. Claude reads the surrounding context to confirm it's a genuine reference, not a coincidental word match.

```
Before: "as described in the API Standards document"
After:  "as described in the [[API Standards]] document"
```

**Reference links** — files that discuss related topics but don't mention each other by name get a `## Related` section appended.

```markdown
## Related
- [[Billing Incident Post-mortem]] — covers the same payment retry failure
- [[API Error Handling Standards]] — overlapping error handling patterns
```

### Report Format

```
## Link Discovery Report

### Inline Links (3 proposed)
ClickUp/Engineering/Payment Processing.md:
  Line 12: "...the API Standards..." → "...the [[API Standards]]..."

### Reference Links (2 proposed)
ClickUp/Engineering/Payment Processing.md:
  Add to ## Related:
    - [[Billing Incident Post-mortem]] — same payment failure scenario

### Summary
- Files scanned: 65
- Inline links proposed: 3
- Reference links proposed: 2
- Files to be modified: 2
```

When confirming, partial approvals are accepted: "only inline", "skip ClickUp/X.md", etc.

### Error Handling

| Error | Message |
|-------|---------|
| Empty vault / path not found | "No .md files found. Check vault root or --path argument." |
| No connections found | "No new connections discovered." |
| File read failure | Skipped, reported in summary |
