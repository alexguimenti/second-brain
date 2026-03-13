# Second Brain

A knowledge management system that turns an Obsidian vault into a queryable context source for Claude Code. Drop any markdown file into the vault — project docs, meeting notes, research, specs, API references, personal notes — and `/vault` makes it searchable from any Claude Code session. Built-in integrations with ClickUp (document sync) and Claude Code (session summaries) are included, but the vault works with any content you put in it.

## System Overview

```
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │   ClickUp    │  │  Any Claude   │  │  Any Source   │
  │  Documents   │  │   Session     │  │  (manual)     │
  └──────┬───────┘  └───────┬──────┘  └───────┬──────┘
         │                  │                  │
         │ /sync-clickup    │ /save-session    │ drop .md files
         ▼                  ▼                  ▼
  ┌────────────────────────────────────────────────────┐
  │                  Obsidian Vault                     │
  │                                                    │
  │  ClickUp docs ─ Sessions ─ Notes ─ Specs ─ ...    │
  │  Any .md file in the vault is searchable           │
  └─────────────────────────┬──────────────────────────┘
                            │ /vault <keywords>
                            ▼
                     ┌──────────────┐
                     │   Context    │
                     │   Loaded     │
                     └──────────────┘
```

The vault is just a folder of markdown files. `/vault` searches **everything** in it — regardless of where the content came from. You can add files manually, sync them from external tools, or generate them from scripts. If it's a `.md` file in the vault, `/vault` will find it.

## Quick Start

1. **Clone** the repository:
   ```bash
   git clone <repo-url> ~/Projects/second-brain
   ```

2. **Install** the slash commands:
   ```bash
   bash scripts/install.sh
   ```

3. **Open** your Obsidian vault (default: `~/Documents/Vault`)

4. **Test** in any Claude Code session:
   ```
   /vault --types
   /vault reliability plan
   ```

## Usage: Loading Context into a Conversation

The main use case: you're in a Claude Code session working on something and need context from your vault — past decisions, product docs, session notes. Here's how it works in practice:

### Step 1: Search your vault

```
/vault billing retry logic
```

Claude searches all your vault files and shows **summary cards** — short descriptions of each match, without loading anything into context:

```
## Vault Search: "billing retry logic"

[1] Payment Processing Architecture
    ClickUp/Engineering/Payment Processing Architecture.md
    → Covers retry strategies for failed payments, exponential backoff
      configuration, and dead letter queue handling.

[2] Billing Incident Post-mortem (Feb 2026)
    Claude Code/Sessions/2026-02-15-billing-incident.md
    → Session where we debugged duplicate charges caused by missing
      idempotency keys in the retry loop.

[3] API Error Handling Standards
    ClickUp/Engineering/API Error Handling Standards.md
    → Company-wide error handling guide. Section on retryable vs
      non-retryable errors with status code mapping.

Say "load 1,3" to bring full documents into context.
```

This costs **~300 tokens** — just summaries and paths.

### Step 2: Load only what you need

```
load 1,3
```

Now only those 2 files are loaded into your conversation (~4K tokens instead of ~10K for all 3). You keep the rest of your context window for actual work.

### Step 3: Continue working

The loaded documents are now part of your conversation context. Claude can reference them as you work — code, debug, plan, or ask questions about the content.

### Other ways to pull context

```
/vault --path ClickUp/Engineering    # Load all files in a folder
/vault --type session                # List all past session summaries
/vault --type session deployment     # Search "deployment" within sessions only
/vault --types                       # See what's in your vault
```

### Saving context for later

At the end of a session, save what you did:

```
/save-session
```

This creates a structured note in `Claude Code/Sessions/` with decisions, outcomes, and a resume command. Next time you need that context, `/vault` will find it.

### Syncing external docs

Keep your vault up to date with ClickUp documents:

```
/sync-clickup                        # Sync all tracked documents
/sync-clickup --discover             # Find new ClickUp docs to track
/sync-clickup --add <id> <name> <path>  # Add a document to track
```

### Keeping your vault connected

As your vault grows, run `/link-vault` to discover connections between files:

```
/link-vault --dry-run              # Preview what links would be created
/link-vault                        # Scan vault and apply with confirmation
/link-vault --path ClickUp/        # Scan only a specific folder
/link-vault my-file.md             # Scan a single file
```

The command finds two types of links:
- **Inline links** — text that mentions another file by name gets wrapped in `[[wikilinks]]`
- **Reference links** — files about related topics get a `## Related` section with connections

Claude reads the context around each mention to judge whether it's a real reference or a coincidental word match — no false positives.

## Commands Reference

| Command | Usage | Description |
|---------|-------|-------------|
| `/vault` | `/vault <keywords>` | Search vault, show summaries, load on demand |
| `/vault` | `/vault --path <folder>` | Load all files in a vault folder |
| `/vault` | `/vault --type <type>` | Filter files by document type |
| `/vault` | `/vault --types` | List available types and file counts |
| `/sync-clickup` | `/sync-clickup` | Sync all tracked ClickUp documents |
| `/sync-clickup` | `/sync-clickup --discover` | Find ClickUp docs to track |
| `/sync-clickup` | `/sync-clickup --add <id> <name> <path>` | Add a document to track |
| `/save-session` | `/save-session [title]` | Save current session summary to vault |
| `/link-vault` | `/link-vault` | Discover and create wikilinks between vault files |
| `/link-vault` | `/link-vault --dry-run` | Preview proposed links without applying |
| `/link-vault` | `/link-vault --path <folder>` | Scan only a specific folder |

See [docs/commands.md](docs/commands.md) for the full reference with all modes and options.

## Vault Structure

```
Vault/
├── ClickUp/                    # Synced ClickUp documents (clickup-doc)
│   ├── <category>/             # Organized by your ClickUp workspace
│   └── sync-config.json        # Sync configuration
├── Claude Code/
│   ├── Sessions/               # Session summaries from /save-session (session)
│   └── Tools/                  # Tool design docs (tool)
└── <your-folders>/             # Custom folders — any structure you want (note)
    └── *.md
```

Types in parentheses are inferred from path when frontmatter `type:` is absent.

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| **Live Grep+Glob, no index** | At <1000 files, Grep is <10ms. An index adds 15K tokens of overhead, is always stale, and LLM-managed JSON is fragile. |
| **LLM-judged ranking** | Claude reads content snippets from Grep to judge relevance — better than metadata-only ranking. |
| **Summary-first, load on demand** | Search shows 2-3 line summaries (~300 tokens) instead of auto-loading full documents (~10K tokens). User picks which files to load. |
| **Prompt-as-code** | Slash commands are versioned markdown files. Edit, review, and deploy like source code. |
| **One-way ClickUp sync** | ClickUp is the source of truth. Vault is read-only mirror. Simplifies conflict resolution to "always overwrite." |

See [docs/architecture.md](docs/architecture.md) for the full design document.

## Roadmap

| Phase | What | Trigger |
|-------|------|---------|
| **1. Slash Commands** (current) | `/vault`, `/sync-clickup`, `/save-session` | — |
| **2. MCP Server** | Automatic vault context in every session | Vault needed 3+ times daily |
| **3. RAG / Vector Index** | Semantic search via embeddings | 10K+ files or keyword search fails |

## License

MIT
