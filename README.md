# Second Brain

A knowledge management system and two-stage AI intelligence loop built on an Obsidian vault. Includes dual search (QMD + LightRAG), automatic persistence, scheduled integrations with ClickUp and Linear, and a nightly intelligence pipeline that surfaces PM blind spots and researches actionable topics using Claude + Gemini.

## System Overview

```
  DATA SOURCES                         GLOBAL MEMORY
  ────────────                         ─────────────
  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐
  │   ClickUp    │  │   Linear     │  │  ~/.claude/           │
  │  Docs + Chat │  │   Tickets    │  │  CLAUDE.md (loader)   │
  └──────┬───────┘  └──────┬───────┘  │  USER.md  (profile)   │
         │                 │          │  SOUL.md  (behavior)   │
  /sync-clickup     /sync-linear      │  MEMORY.md (knowledge) │
         │                 │          └──────────┬────────────┘
         ▼                 ▼                     │ loaded every session
  ┌────────────────────────────────────┐         │
  │          Obsidian Vault            │         │
  │                                    │         │
  │  ClickUp docs ─ Linear snapshots  │         │
  │  Chat snapshots ─ Sessions ─ EODs │         │
  │  Insights ─ Research ─ Daily logs │         │
  └──┬──────────────┬─────────────┬───┘         │
     │              │             │              │
     │ QMD          │ LightRAG    │ /vault       │
     │ (documents)  │ (graph)     │ (explicit)   │
     ▼              ▼             ▼              ▼
  ┌────────────────────────────────────────────────┐
  │              Claude Code Session                │
  └────────────────────┬───────────────────────────┘
                       │ On close (Ctrl+C)
  ┌────────────────────▼───────────────────────────┐
  │  SessionEnd Hook → auto-backup to vault        │
  └────────────────────────────────────────────────┘

  INTELLIGENCE LOOP (nightly, fully automatic)
  ─────────────────────────────────────────────
  21:00  Insight Agent  → reads vault (sessions, memory, chat, product docs)
                        → runs blind-spots lens via Claude
                        → saves to Vault/Work/Insights/{date}.md
                        → posts summary to ClickUp

  21:15  Research Agent → picks top 3 topics from insight
                        → fetches live data via Gemini 2.5
                        → synthesizes with Claude
                        → saves to Vault/Work/Research/{date}.md
                        → posts summary to ClickUp

  Mon    Insight Agent  → runs weekly lens (exec brief with 🟢/🟡/🔴 scorecard)
  08:00

  SCHEDULED TASKS (Windows Task Scheduler)
  ─────────────────────────────────────────
  07:00 + 13:00  Sync ClickUp + Linear + Chat + QMD re-index
  18:30          /daily-recap → consolidate sessions into Vault/Work/Daily/
  19:00          Daily reflection → curate MEMORY.md
  20:00          Link vault → discover document connections
  21:00          Insight Agent (blind-spots lens)
  21:15          Research Agent (Gemini + Claude)
  Mon 08:00      Insight Agent (weekly exec brief)
```

The vault is a folder of markdown files with two search engines: **QMD** (semantic document search, local, free) and **LightRAG** (knowledge graph with entity relationships, OpenAI-powered). Claude has persistent identity across all sessions via 4 global files and automatically backs up every session on close. A nightly intelligence loop reads the vault and generates actionable insights and research briefs.

## Quick Start

1. **Clone** the repository:
   ```bash
   git clone <repo-url> ~/Projects/second-brain
   ```

2. **Install** the slash commands:
   ```bash
   bash scripts/install.sh
   ```

3. **Set up QMD** (semantic search — recommended):
   ```bash
   bash scripts/setup-qmd.sh
   ```

4. **Set up LightRAG** (knowledge graph — optional):
   ```bash
   bash scripts/setup-lightrag.sh
   ```

5. **Register scheduled tasks:**
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts\register-scheduled-sync.ps1
   powershell -ExecutionPolicy Bypass -File scripts\register-daily-reflection.ps1
   powershell -ExecutionPolicy Bypass -File scripts\register-daily-link-vault.ps1
   ```

6. **Test** in any Claude Code session:
   ```
   /vault --types                        # Browse vault
   /vault reliability plan               # Search with QMD
   /lightrag-query how does X relate to Y?  # Graph search
   /lightrag-status                      # Check LightRAG health
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
| `/sync-linear` | `/sync-linear [team]` | Sync Linear ticket snapshots to vault |
| `/sync-clickup-chat` | `/sync-clickup-chat` | Sync ClickUp chat channel snapshots |
| `/lightrag-query` | `/lightrag-query <question>` | Query knowledge graph (hybrid search) |
| `/lightrag-explore` | `/lightrag-explore <entity>` | Explore graph entities and connections |
| `/lightrag-upload` | `/lightrag-upload <file>` | Upload document to knowledge graph |
| `/lightrag-status` | `/lightrag-status` | Check LightRAG health and indexing status |
| `/end-session` | `/end-session` | Run /log + /save-session, then Ctrl+C to close |

See [docs/commands.md](docs/commands.md) for the full reference with all modes and options.

## Vault Structure

```
Mex_Vault/
├── Personal/                        # Personal notes (note)
├── Tools/                           # Tool docs + global memory copies
│   ├── USER.md                      # User profile (synced from ~/.claude/)
│   ├── SOUL.md                      # Behavior rules (synced from ~/.claude/)
│   ├── MEMORY.md                    # Curated knowledge (synced from ~/.claude/)
│   └── CC/                          # Claude Code tool documentation
└── Work/
    ├── ClickUp/                     # Synced ClickUp documents (clickup-doc)
    │   ├── Chat/                    # Chat channel snapshots (clickup-chat)
    │   │   └── DM/                  # Direct message snapshots
    │   ├── sync-config.json         # Doc sync configuration
    │   └── chat-sync-config.json    # Chat sync configuration
    ├── Linear/                      # Linear ticket snapshots (linear-snapshot)
    │   ├── LLMV.md                  # LLM Visibility team snapshot
    │   ├── RB.md                    # Report Builder team snapshot
    │   └── GSC.md                   # GSC team snapshot
    ├── Claude Code/
    │   └── Sessions/                # Session summaries (session)
    │       └── auto/                # Auto-backups from hook (session-auto)
    ├── EOD/                         # End-of-day summaries (eod)
    └── Search Atlas/                # Search Atlas project docs (search-atlas)
```

Types in parentheses are inferred from path when frontmatter `type:` is absent.

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| **Dual search: QMD + LightRAG** | QMD for document search (keyword + vector + re-ranking). LightRAG for graph queries (entities + relationships). Complementary, not competing. |
| **QMD hybrid search (document search)** | BM25 + vector embeddings + LLM re-ranking via local MCP. Semantic matches ("payment failures" → "billing retry"). Registered globally — works in any session. Zero cost (local models). |
| **LightRAG graph search (relationship queries)** | Knowledge graph maps entities and connections. Answers "how does X relate to Y?" Better for cross-document reasoning. Uses OpenAI API (~$0.01-0.05/query). |
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

QMD runs 100% locally (local models, no API calls). LightRAG uses OpenAI API for embeddings and graph extraction (~$0.01-0.05/query) — document content is sent to OpenAI during indexing and queries. The vault itself is a local folder. Claude reads files directly from disk.

**Do I need Obsidian installed?**

No. The vault is just a folder of markdown files. Obsidian is optional for browsing and editing, but the commands work with any folder of `.md` files.

**Can I use this with sources other than ClickUp?**

Yes. The vault works with any markdown file. Drop `.md` files manually, sync them from other tools, or generate them with scripts. `/sync-clickup` is one built-in integration, but the vault itself is source-agnostic.

**How does search work?**

Three search engines, each for different use cases:

| Engine | Best for | Cost | Command |
|--------|---------|------|---------|
| **QMD** | "Find docs about X" | Free (local) | Automatic via MCP, or `/vault` |
| **LightRAG** | "How does X relate to Y?" | ~$0.01-0.05/query (OpenAI) | `/lightrag-query` |
| **Grep/Glob** | Fallback when QMD unavailable | Free | `/vault` (automatic fallback) |

**Do I need to use commands every time?**

No. QMD is registered globally — Claude searches the vault automatically when it needs context. LightRAG requires explicit `/lightrag-query` commands. `/vault` is for controlled browsing with summary cards.

**What's the difference between QMD and LightRAG?**

QMD finds **documents** relevant to your query. LightRAG finds **entities and relationships** — it understands that "Omar" is "Lead of LLMv" who "reported to Alexandre" who "decided to delay the credit system launch." Use QMD for most searches, LightRAG when you need to understand connections.

**How do I add my own files to the vault?**

Drop any `.md` file into your vault folder. You can organize files in any subfolder structure you want. `/vault` searches everything recursively.

**Can multiple people share the same vault?**

Not currently. The vault is designed as a personal knowledge base on a single machine. Each person sets up their own vault with their own content.

## Roadmap — Complete

All 7 phases implemented. Inspired by [second-brain-starter](https://github.com/coleam00/second-brain-starter), adapted for a PM workflow with Claude Code + Obsidian + ClickUp + Linear + Gemini.

| Phase | What | Status |
|-------|------|--------|
| **1. Slash Commands** | `/vault`, `/sync-clickup`, `/save-session`, `/link-vault` | ✅ |
| **2. QMD Hybrid Search + MCP** | Semantic search, automatic context loading | ✅ |
| **3. Automatic Persistence (Hooks)** | Session auto-backup, daily log feed into `/eod` | ✅ |
| **4. Structured Memory** | USER.md + SOUL.md + MEMORY.md + CLAUDE.md loaded globally | ✅ |
| **5. Expanded Integrations** | Linear + ClickUp + Chat sync, scheduled 2x daily | ✅ |
| **6. Automatic Curation** | Daily reflection, PreCompact hook, MEMORY.md auto-curated | ✅ |
| **7. Intelligence Loop** | Insight Agent (blind-spots/weekly) + Research Agent (Gemini + Claude) | ✅ |

### Phase 2 — QMD Hybrid Search + MCP ✅

[QMD](https://github.com/tobi/qmd) is installed as a local MCP server registered globally in `~/.claude.json`. Claude can now search the vault automatically from **any session in any project** — no `/vault` command needed.

**What's working:**
- QMD hybrid search (BM25 + vector embeddings + LLM re-ranking) via MCP
- 455 files indexed, 967 vectors embedded
- Context metadata configured per vault folder for better ranking
- `/vault` uses QMD as preferred backend, Grep/Glob as fallback
- Global MCP registration — works in every Claude Code session

### Phase 3 — Automatic Persistence (Hooks) ✅

Every non-trivial session (3+ user messages) is automatically backed up when it ends.

**What's working:**
- SessionEnd hook runs `scripts/session-backup.py` on every session close
- Lightweight markdown note saved to `Work/Claude Code/Sessions/auto/`
- Session summary appended to `~/.claude/daily-logs/YYYY-MM-DD.md` — feeds into `/eod`
- Global config files (USER.md, SOUL.md, CLAUDE.md) synced to vault on every close
- Close with `/exit` or `Ctrl+C` (not the X button) to trigger the hook

### Phase 4 — Structured Memory ✅

Global context files give Claude persistent identity across all sessions and projects.

**What's working:**
- `~/.claude/CLAUDE.md` — orchestrator that loads USER.md, SOUL.md, and MEMORY.md in every session
- `~/.claude/USER.md` — user profile (role, teams, tools). Claude updates when it learns new info
- `~/.claude/SOUL.md` — behavior rules (communication, guardrails, Linear conventions). Manual edit only
- `~/.claude/MEMORY.md` — curated knowledge (decisions, initiatives, lessons). Claude updates on important decisions
- All four synced to `<vault>/Tools/` on every session close

### Phase 5 — Expanded Integrations ✅

All major data sources synced to vault automatically.

**What's working:**
- `/sync-clickup` — one-way ClickUp doc sync (10 tracked docs)
- `/sync-linear` — Linear ticket snapshots per team (LLMV, RB, GSC)
- `/sync-clickup-chat` — ClickUp chat snapshots (14 channels + 14 DMs)
- Scheduled sync — Windows Task Scheduler runs all 3 syncs + QMD re-index at 07:00 and 13:00
- Linear + ClickUp connected via MCP — accessible from any session

### Phase 6 — Automatic Curation ✅

Context is automatically preserved and curated without manual effort.

**What's working:**
- Daily reflection at 19:00 — reviews daily log and promotes important decisions to MEMORY.md
- PreCompact hook — extracts topics and decisions before context truncation in long sessions
- MEMORY.md auto-curated — stale entries removed, new decisions added with dates
- Daily link-vault at 20:00 — discovers connections between vault documents, creates wikilinks, re-indexes QMD

### Phase 7 — Intelligence Loop ✅

A two-stage AI pipeline that reads the vault every night and generates actionable insights and research briefs — no manual effort required.

**Stage 1 — Insight Agent (`scripts/insight-agent.py`):**
- Reads ~120K chars of context: session notes, daily logs, MEMORY.md, product docs, ClickUp chat snapshots, previous insights
- Runs one of three analytical lenses via Claude:
  - `blind-spots` — attention gaps, assumption risks, neglected products, stale threads
  - `patterns` — cross-product themes, repeated decisions, convergence opportunities
  - `weekly` — one-page exec brief with 🟢/🟡/🔴 scorecard per product
- Saves to `Vault/Work/Insights/{date}-{lens}.md` and posts summary to ClickUp

**Stage 2 — Research Agent (`scripts/research-agent.py`):**
- Reads the latest insight report
- Uses Claude to extract top 3 research topics
- Fetches live web data via Gemini 2.5 Flash (with Claude fallback if unavailable)
- Synthesizes a structured brief per topic: what's happening, best practices, recommended actions, signals to watch
- Saves to `Vault/Work/Research/{date}-research.md` and posts to ClickUp

**Run manually:**
```bash
CLAUDE_SILENT_STOP=1 python3 scripts/insight-agent.py --lens blind-spots
CLAUDE_SILENT_STOP=1 python3 scripts/insight-agent.py --lens weekly
CLAUDE_SILENT_STOP=1 python3 scripts/insight-agent.py --dry-run   # preview context only
CLAUDE_SILENT_STOP=1 python3 scripts/research-agent.py
CLAUDE_SILENT_STOP=1 python3 scripts/research-agent.py --topic "SLA breach playbook"
```

**Note:** `CLAUDE_SILENT_STOP=1` prevents the save-session hook from interfering with automated Claude CLI calls.

---

### Daily Automation Schedule

| Time | Task | What it does |
|------|------|-------------|
| **07:00** | Sync | ClickUp docs + Linear tickets + ClickUp chat + QMD + LightRAG re-index |
| **13:00** | Sync | Same as 07:00 (second daily run) |
| **18:30** | Daily recap | Consolidates Claude sessions into `Vault/Work/Daily/{date}.md` |
| **19:00** | Reflection | Reviews daily log, curates MEMORY.md |
| **20:00** | Link vault | Discovers document connections, creates wikilinks, QMD re-index |
| **21:00** | Insight Agent | Blind-spots lens → `Vault/Work/Insights/` + ClickUp |
| **21:15** | Research Agent | Top 3 topics via Gemini + Claude → `Vault/Work/Research/` + ClickUp |
| **Mon 08:00** | Weekly brief | Weekly exec brief (scorecard per product) → `Vault/Work/Insights/` + ClickUp |
| **On close** | Session backup | Auto-backup + daily log + sync global files (Ctrl+C or /exit) |
| **On compact** | PreCompact | Extracts topics/decisions before context truncation |

## License

MIT
