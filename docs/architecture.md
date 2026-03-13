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
   │  Top 3 auto-loaded  │  ← context budget guard
   │  Rest listed for    │     max 3, large file warning
   │  manual loading     │
   └─────────────────────┘
```

### Ranking Signals

Claude uses these signals to pick the top 3 files:

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
| `Search Atlas/EOD/` | `eod` | End-of-day reports |
| `Search Atlas/Daily/` | `daily` | Daily notes |
| Everything else | `note` | General notes |

Users can override with a `type:` field in YAML frontmatter.

## Context Budget Guard

To prevent context window blowout:

- **Max 3 files** auto-loaded per search
- **Large file warning** before loading known-large documents
- **Grep head_limit** caps snippet output at ~200 lines (~15-20 files)
- **User-initiated loading** for additional matches via `load N` syntax

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
| 2026-03-13 | Vault-wide search across all folders | No restrictions — includes ClickUp, sessions, EODs, tools, future content |
| 2026-03-13 | Defer index to Phase 3 at 10K+ files | Gemini analysis: Grep noise is the only valid trigger, happens at much larger scale |
