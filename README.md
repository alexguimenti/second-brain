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
  └──────────┬──────────────────────────┬──────────────┘
             │                          │
             │ QMD MCP (automatic)      │ /vault <keywords>
             │ Claude searches on       │ (explicit search)
             │ its own when needed      │
             ▼                          ▼
                     ┌──────────────┐
                     │   Context    │
                     │   Loaded     │
                     └──────────────┘
```

The vault is just a folder of markdown files. With QMD installed, Claude can search the vault **automatically from any session in any project** — no explicit commands needed. The `/vault` command remains available for deliberate browsing and controlled context loading. You can add files manually, sync them from external tools, or generate them with scripts. If it's a `.md` file in the vault, it's searchable.

## Quick Start

1. **Clone** the repository:
   ```bash
   git clone <repo-url> ~/Projects/second-brain
   ```

2. **Install** the slash commands:
   ```bash
   bash scripts/install.sh
   ```

3. **Set up QMD** (optional but recommended — enables semantic search from any session):
   ```bash
   bash scripts/setup-qmd.sh
   ```

4. **Open** your Obsidian vault (default: `~/Documents/Vaults/Mex_Vault`)

5. **Test** in any Claude Code session:
   ```
   /vault --types
   /vault reliability plan
   ```
   With QMD installed, you can also just ask Claude directly — e.g., "what do we have about reliability?" — and it will search the vault automatically.

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
    Work/ClickUp/Engineering/Payment Processing Architecture.md
    → Covers retry strategies for failed payments, exponential backoff
      configuration, and dead letter queue handling.

[2] Billing Incident Post-mortem (Feb 2026)
    Work/Claude Code/Sessions/2026-02-15-billing-incident.md
    → Session where we debugged duplicate charges caused by missing
      idempotency keys in the retry loop.

[3] API Error Handling Standards
    Work/ClickUp/Engineering/API Error Handling Standards.md
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
/vault --path Work/ClickUp/Engineering    # Load all files in a folder
/vault --type session                # List all past session summaries
/vault --type session deployment     # Search "deployment" within sessions only
/vault --types                       # See what's in your vault
```

### Saving context for later

Every session is backed up automatically when you close with `Ctrl+C` (3+ messages required). For a richer note:

```
/end-session    → runs /log + /save-session, then press Ctrl+C
```

| How you close | What gets saved |
|---------------|----------------|
| `Ctrl+C` only | Auto-backup (user messages + resume command) |
| `/end-session` + `Ctrl+C` | Structured note (decisions, wikilinks, insights) + auto-backup |

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
/link-vault --path Work/ClickUp/        # Scan only a specific folder
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
Mex_Vault/
├── Personal/                   # Personal notes (note)
├── Tools/                      # Tool design docs (tool)
└── Work/
    ├── ClickUp/                # Synced ClickUp documents (clickup-doc)
    │   ├── <category>/         # Organized by your ClickUp workspace
    │   └── sync-config.json    # Sync configuration
    ├── Claude Code/
    │   └── Sessions/           # Session summaries from /save-session (session)
    ├── EOD/                    # End-of-day summaries (eod)
    └── Search Atlas/           # Search Atlas project docs (search-atlas)
```

Types in parentheses are inferred from path when frontmatter `type:` is absent.

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| **QMD hybrid search (preferred)** | BM25 + vector embeddings + LLM re-ranking via local MCP. Semantic matches ("payment failures" → "billing retry"). Registered globally — works in any session. |
| **Grep/Glob fallback** | At <1000 files, Grep is <10ms. Works without QMD setup. Automatic fallback when QMD MCP is unavailable. |
| **Global MCP, not per-project** | QMD registered in `~/.claude.json` (global). Claude can search the vault from any project without `/vault` — just ask. |
| **Summary-first, load on demand** | Search shows 2-3 line summaries (~300 tokens) instead of auto-loading full documents (~10K tokens). User picks which files to load. |
| **Prompt-as-code** | Slash commands are versioned markdown files. Edit, review, and deploy like source code. |
| **One-way ClickUp sync** | ClickUp is the source of truth. Vault is read-only mirror. Simplifies conflict resolution to "always overwrite." |

See [docs/architecture.md](docs/architecture.md) for the full design document.

## FAQ

**What's the difference between `/save-session` and telling Claude to save something to a file?**

`/save-session` creates a structured note with consistent sections (decisions, outcomes, resume command) and saves it to a specific location in the vault (`Work/Claude Code/Sessions/`). Because all sessions follow the same format and live in the same place, `/vault` can find them later. If you tell Claude "save this to a README," it works for that moment, but the file ends up in a random project folder with no consistent format, and `/vault` won't find it.

**Does this send my data anywhere?**

No. Everything runs locally. The vault is a folder on your machine, QMD runs a local MCP server with local models (~1.9GB cached in `~/.cache/qmd/`), and Claude reads files directly from disk. No data leaves your environment.

**Do I need Obsidian installed?**

No. The vault is just a folder of markdown files. Obsidian is optional for browsing and editing, but the commands work with any folder of `.md` files.

**Can I use this with sources other than ClickUp?**

Yes. The vault works with any markdown file. Drop `.md` files manually, sync them from other tools, or generate them with scripts. `/sync-clickup` is one built-in integration, but the vault itself is source-agnostic.

**How does search work?**

With QMD installed (recommended), Claude searches the vault automatically using hybrid search — BM25 keyword matching, vector semantic search, and LLM re-ranking. This works from **any Claude Code session in any project**, not just inside the second-brain repo. You can also use `/vault` explicitly for controlled browsing with summary cards and selective loading.

Without QMD, `/vault` falls back to Grep/Glob keyword search — still fast (<10ms for <1000 files), but without semantic matching.

**Do I need to use `/vault` every time I want vault context?**

No. With QMD installed, Claude can search the vault on its own — just ask a question and it will pull relevant context automatically via MCP. `/vault` is still useful when you want to browse, preview summaries, or control exactly which files get loaded into context.

**How do I add my own files to the vault?**

Drop any `.md` file into your vault folder. You can organize files in any subfolder structure you want. `/vault` searches everything recursively.

**Can multiple people share the same vault?**

Not currently. The vault is designed as a personal knowledge base on a single machine. Each person sets up their own vault with their own content.

## Roadmap

| Phase | What | Status |
|-------|------|--------|
| **1. Slash Commands** | `/vault`, `/sync-clickup`, `/save-session`, `/link-vault` | ✅ Complete |
| **2. QMD Hybrid Search + MCP** | Semantic search, automatic context loading | ✅ Complete |
| **3. Automatic Persistence (Hooks)** | Session auto-backup on close, daily logs | 🔧 In Progress |
| **4. Structured Memory** | USER.md + SOUL.md loaded globally, MEMORY.md curated | 🔧 In Progress |
| **5. Expanded Integrations** | Linear sync, bidirectional ClickUp, scheduled sync | Planned |
| **6. Proactive Monitoring** | Heartbeat system, OS/Slack notifications, state diffing | Planned |

### Phase 2 — QMD Hybrid Search + MCP ✅

[QMD](https://github.com/tobi/qmd) is installed as a local MCP server registered globally in `~/.claude.json`. Claude can now search the vault automatically from **any session in any project** — no `/vault` command needed.

**What's working:**
- QMD hybrid search (BM25 + vector embeddings + LLM re-ranking) via MCP
- 455 files indexed, 967 vectors embedded
- Context metadata configured per vault folder for better ranking
- `/vault` uses QMD as preferred backend, Grep/Glob as fallback
- Global MCP registration — works in every Claude Code session

### Phase 3 — Automatic Persistence (Hooks) 🔧

Session auto-backup is live. Every non-trivial session (3+ user messages) is saved to the vault automatically when the session ends.

**What's working:**
- SessionEnd hook runs `scripts/session-backup.py` on every session close
- Extracts user messages from the transcript and writes a lightweight markdown note
- Notes saved to `Work/Claude Code/Sessions/auto/` with `session-auto` type
- Searchable via `/vault` and QMD — complements manual `/save-session`

**Still planned:**
- Daily log aggregation (`Work/Claude Code/Daily/YYYY-MM-DD.md`)
- PreCompact hook for extracting decisions before context truncation

### Phase 4 — Structured Memory 🔧

Global context files give Claude persistent identity across all sessions and projects.

**What's working:**
- `~/.claude/USER.md` — user profile (role, teams, tools). Claude updates when it learns new info
- `~/.claude/SOUL.md` — behavior rules (communication, guardrails, Linear conventions). Manual edit only
- `~/.claude/CLAUDE.md` — orchestrator that loads USER.md and SOUL.md in every session
- Session-backup hook syncs all three to `<vault>/Tools/` on every session close

**Still planned:**
- Curated MEMORY.md with promoted decisions from daily logs

### Phase 5 — Expanded Integrations

Bring more data sources into the vault automatically.

**Steps:**
1. Expand `/sync-clickup` with more granular sync options
2. Add Linear sync (already connected via MCP)
3. Scheduled sync via cron/task scheduler

**Key benefit:** More complete vault = more useful search results.

### Phase 6 — Proactive Monitoring (Heartbeat)

Claude actively monitors your tools and notifies you about relevant changes.

**Steps:**
1. Python script running every 30 minutes via cron
2. Pull data from ClickUp/Linear/connected platforms
3. State diffing against previous snapshot
4. Notify via OS notifications or Slack when something relevant changes

**Key benefit:** You get notified before you need to ask.

## License

MIT
