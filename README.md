# Second Brain

A knowledge management system that turns an Obsidian vault into a queryable context source for Claude Code. Syncs ClickUp documents, saves session summaries, and lets you search everything with natural language — all through slash commands.

## System Overview

```
                    ┌──────────────┐
                    │   ClickUp    │
                    │  Documents   │
                    └──────┬───────┘
                           │ /sync-clickup
                           ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Claude Code  │───▶│   Obsidian   │◀───│   Session    │
│  Sessions    │    │    Vault     │    │  Summaries   │
└──────────────┘    └──────┬───────┘    └──────────────┘
                           │                    ▲
                           │ /vault             │ /save-session
                           ▼                    │
                    ┌──────────────┐    ┌───────┴──────┐
                    │   Context    │    │  Any Claude   │
                    │   Loaded     │    │   Session     │
                    └──────────────┘    └──────────────┘
```

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

## Commands

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

### /save-session

Run `/save-session` at the end of any Claude Code session (in any project) to capture a structured summary in the vault. The command:

- Extracts context, decisions, outcomes, and insights from the conversation
- Detects if the session already has a note (one session = one note, even across resumes)
- Discovers related vault notes and links them via Obsidian wikilinks
- Writes a markdown file to `Claude Code/Sessions/` with frontmatter and a resume command

This builds a searchable log of everything you've done across all projects. Use `/vault --type session` or `/vault <keywords>` to find past sessions later.

```
/save-session                    # Auto-generate title
/save-session deployment fix     # Custom title slug
```

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
