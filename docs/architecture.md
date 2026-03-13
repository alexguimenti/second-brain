# Architecture

## Design Philosophy

The Second Brain system treats **Claude's native tools as a search engine**. Rather than building a separate index or database, it leverages the Glob and Grep tools already available in every Claude Code session to search the vault in real time. Claude itself acts as the ranking algorithm, reading content snippets to judge relevance.

This approach follows two principles:

1. **Prompt-as-code** — Slash commands are versioned markdown files that Claude interprets as instructions. They are deterministic, reviewable, and deployable like source code.
2. **Zero infrastructure** — No servers, databases, or background processes. The vault is a folder of markdown files. The commands are markdown files. Everything is portable and inspectable.

## Why Live Grep+Glob (No Index)

The original design included a `.vault-index.json` file maintained by Claude. An adversarial review (Claude + Gemini) identified 5 critical flaws:

| # | Flaw | Impact | Resolution |
|---|------|--------|------------|
| 1 | Index premature at ~65 files | 50KB overhead (~15K tokens) loaded on every invocation | Dropped index — live Grep is <10ms |
| 2 | Search priority hid body content | Title matches filling top 3 prevented finding buried information | Always search body via Grep — snippets are primary ranking signal |
| 3 | Stale index guaranteed | New files invisible until manual reindex | No index = always fresh |
| 4 | LLM-as-database fragile | JSON corruption risk during reindex, 30-60s of token-heavy processing | No index = no corruption risk |
| 5 | Metadata inferior to snippets | Titles/headings less informative than actual matching sentences | Claude ranks based on Grep snippets (actual content around keywords) |

**Consensus:** Live search now, proper database (SQLite/vector) via MCP only when Grep becomes too noisy (estimated at 10K+ files).

## Search Architecture

```
User: /vault reliability plan
         │
         ▼
┌─────────────────────────────────┐
│        Parse Arguments          │
│   mode = keyword_search         │
└─────────┬───────────────────────┘
          │
          ├──────────────┐
          ▼              ▼
   ┌────────────┐ ┌────────────┐
   │    Glob    │ │    Grep    │  ← parallel execution
   │  filename  │ │  content   │
   │  matching  │ │  snippets  │
   └─────┬──────┘ └─────┬──────┘
         │              │
         └──────┬───────┘
                ▼
   ┌─────────────────────┐
   │   Claude synthesizes │  ← LLM judges relevance
   │   - filename signal  │     from actual content
   │   - content signal   │
   │   - heading context  │
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Summary cards      │  ← 2-3 lines per file
   │  generated from     │     from snippets only
   │  snippets           │     (~300 tokens total)
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  User: "load 1,3"   │  ← on-demand loading
   │  Full files loaded   │     only what's needed
   └─────────────────────┘
```

### Ranking Signals

Claude uses these signals to rank files and generate summary cards:

| Signal | Strength | Source |
|--------|----------|--------|
| Keyword in filename/path | Strong | Glob results |
| Keyword in heading or frontmatter | Strong | Grep snippets |
| Keyword in key paragraph | Medium | Grep snippets |
| Keyword in passing mention | Weak | Grep snippets |
| Multiple keyword matches in same file | Strong | Grep match density |

## Type Inference System

Files are classified by type for `--type` filtering. Type comes from frontmatter first, then path inference:

| Path Prefix | Inferred Type | Description |
|-------------|---------------|-------------|
| `ClickUp/` | `clickup-doc` | Synced ClickUp documents |
| `Claude Code/Sessions/` | `session` | Session summaries |
| `Claude Code/Tools/` | `tool` | Tool design documents |
| Everything else | `note` | General notes |

Users can override with a `type:` field in YAML frontmatter. To add custom types, either add frontmatter to your files or extend the path inference table in `commands/vault.md`.

## Context Budget Design

Search results never auto-load files. Instead, the system uses a **summary-first** approach:

- **Summary cards** — 2-3 line descriptions generated from Grep snippets (~300 tokens for 10 results vs ~10K tokens for 3 full documents)
- **On-demand loading** — user picks which files to load via `load N` syntax
- **Large file warning** — before loading files that appear very large
- **Grep head_limit** — caps snippet output at ~200 lines (~15-20 files)
- **Max 10 cards** per search — keeps results scannable

## Phased Roadmap

| Phase | Approach | Trigger to Advance |
|-------|----------|--------------------|
| **1. Slash Commands** (current) | Live Grep+Glob, LLM ranking, 3 commands | — |
| **2. MCP Server** | Obsidian MCP for automatic vault context | Vault needed 3+ times daily across projects |
| **3. RAG / Vector** | SQLite/vector DB with semantic search via MCP | 10K+ files or keyword search consistently noisy |

Each phase is additive — Phase 2 doesn't replace Phase 1, it adds automatic context loading alongside manual `/vault` queries.

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-03-13 | Start with `/vault` slash command | Lowest effort, highest immediate ROI |
| 2026-03-13 | Drop JSON index after adversarial review | Index added 15K tokens overhead, was always stale, LLM-managed JSON is fragile |
| 2026-03-13 | Live Grep+Glob as search engine | <10ms on 65 files, always fresh, zero maintenance |
| 2026-03-13 | Global command (`~/.claude/commands/`) | Must work across all projects, not just the Vault directory |
| 2026-03-13 | Vault-wide search across all folders | No restrictions — includes ClickUp, sessions, tools, and any custom folders |
| 2026-03-13 | Defer index to Phase 3 at 10K+ files | Gemini analysis: Grep noise is the only valid trigger, happens at much larger scale |
