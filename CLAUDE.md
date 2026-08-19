# Second Brain

Canonical source for the Second Brain knowledge management tooling — Obsidian vault integration, dual search (QMD + LightRAG), Claude Code slash commands, ClickUp + Linear sync, and a two-stage nightly intelligence loop (Insight + Research agents).

See [README.md](README.md) for the user-facing overview and Quick Start. This file is the developer/maintainer reference loaded into every session in this repo.

## Key Paths

- **Vault root:** `$HOME/Documents/Vaults/MyVault` (Obsidian vault, not in this repo)
- **Commands deployment target:** `~/.claude/commands/`
- **Sync configs (live):**
  - `<vault>/Work/ClickUp/sync-config.json` — tracked ClickUp docs
  - `<vault>/Work/ClickUp/chat-sync-config.json` — tracked ClickUp chat channels
- **QMD config:** `~/.config/qmd/index.yml` (collection + context config)
- **QMD cache:** `~/.cache/qmd/` (SQLite index + local models)
- **LightRAG service:** `http://localhost:9621` (Docker, see `lightrag/docker-compose.yml`)
- **LightRAG storage:** `lightrag/data/rag_storage/` (graph) + `lightrag/data/inputs/` (staged docs)
- **Intelligence outputs:**
  - `<vault>/Work/Insights/{date}-{lens}.md` (Insight Agent)
  - `<vault>/Work/Research/{date}-research.md` (Research Agent)
- **Global config (loaded every session):** `~/.claude/{CLAUDE,USER,SOUL,MEMORY}.md`

## Conventions

- **Prompt-as-code:** Slash commands are markdown files Claude Code interprets as instructions. Version, review, deploy like source code.
- **Vault path via template:** Commands use `{{VAULT_ROOT}}` placeholder. `install.sh` substitutes it with the resolved `VAULT_ROOT` env var (default: `$HOME/Documents/Vaults/MyVault`).
- **Language:** English for all documentation and command prompts.
- **No inline sensitive constants — ever:** No script may hardcode real ClickUp/Linear IDs, tokens, employee names, or user-ID→name rosters as a literal in committed source, regardless of whether the repo "feels internal." This repo has two git remotes (public GitHub + internal Forge) pushed in lockstep with no filtering step in between (see `SECURITY.md`) — anything committed is instantly live in both. Any identity/secret data a script needs must load at runtime from a local, gitignored file (`<name>.local.json` / `<name>.usermap.json`), with a committed `*.template.json` / `*.example.json` sibling showing the shape and a graceful fallback (e.g. `User <id>`) when the local file is missing. `config/*.template.json` is the existing pattern for sync configs (real config lives in `<vault>/Work/ClickUp/`); `scripts/chat-user-map.example.json` is the pattern for identity rosters. This was violated once (a real employee roster in `scripts/chat-snapshot.py` and siblings, fixed 2026-07-10 via `git filter-repo` + force-push to both remotes) — see `SECURITY.md` for the full incident and the categories of data this covers.
- **Sync direction:** ClickUp + Linear → Vault is one-way. Vault is a read-only mirror; conflict resolution = always overwrite. Never push vault edits upstream.
- **Scratch files:** Use `tmp_*.py` / `tmp_*.json` / `tmp_*.txt` / `tmp_*.md` for experimental scripts, or drop multi-file exploration in `scratch/` — both are gitignored.
- **Cross-runtime availability (added 2026-08-19):** these `commands/*.md` files are deployed by `install.sh` only to `~/.claude/commands/`, so by default they only exist for Claude Code. Each command also has a thin pointer skill at `~/Sync/.agent-config/skills/<name>/SKILL.md` (fanned to Claude/Codex/Gemini/Kimi) that says "read and follow `commands/<name>.md`" — so Codex and Kimi sessions can run `/vault`, `/sync-clickup`, `/link-vault`, etc. too, without duplicating the instructions. **When adding a new command here, add a matching pointer skill** (see any existing one under `~/Sync/.agent-config/skills/` for the template) and run `stack/skills/sync.sh <name>` from the `agentic-engineering` repo to fan it out — otherwise the new command stays Claude-only, silently.

## Workflow

1. Edit commands in `commands/`
2. Run `bash scripts/install.sh` to deploy commands and register `SessionEnd` + `PreCompact` hooks
3. Optional setup: `bash scripts/setup-qmd.sh` (semantic search) and/or `bash scripts/setup-lightrag.sh` (graph search)
4. Optional scheduling: see "Scheduled Tasks" below — three `register-*.ps1` cover sync/reflection/link-vault. Intelligence Loop tasks must be registered manually for now.
5. Test in a Claude Code session (`/vault --types`, `/sync-clickup --discover`)

## Search Engines

The vault is a folder of markdown files. Three engines run against it, picked by use case:

| Engine | Best for | Cost | Backend |
|--------|----------|------|---------|
| **QMD** | "Find docs about X" | Free (local models) | MCP server registered globally in `~/.claude.json` |
| **LightRAG** | "How does X relate to Y?" | OpenAI API (~$0.01–0.05/query) | Local Docker service at `:9621` |
| **Grep/Glob** | Fallback when QMD is unavailable | Free | Built-in tools |

- **QMD scope:** registered globally under `~/.claude.json` → `mcpServers.qmd` — Claude can search the vault from **any** project without explicit `/vault` calls.
- **Re-index after vault changes:** `qmd embed` (incremental) or `qmd embed -f` (full). The scheduled sync and `daily-link-vault.sh` both call `qmd embed` automatically.
- **LightRAG re-index:** `scheduled-sync.sh` copies relevant `.md` files into `lightrag/data/inputs/` and triggers `POST /documents/scan`. Only runs if the LightRAG service responds on `:9621`.

## Hooks

| Hook | Event | Script | What it does |
|------|-------|--------|--------------|
| Session backup | `SessionEnd` | `scripts/session-backup.py` | Lightweight markdown backup of session + append to daily log + sync `~/.claude/{CLAUDE,USER,SOUL,MEMORY}.md` to `<vault>/Tools/`. Skips sessions with < 3 user messages. Type tag: `session-auto` (distinct from `session` written by `/save-session`). |
| Pre-compact | `PreCompact` | `scripts/pre-compact.py` | Extracts topics + decisions before Claude truncates context in long sessions. |

Both hooks are registered automatically by `scripts/install.sh` into `~/.claude/settings.json`.

## Scheduled Tasks

Six recurring tasks, all registered in Task Scheduler — three via `register-*.ps1` in this repo, three registered by hand (no ps1 yet).

| Time | Windows task name | Script | Registered by |
|------|-------------------|--------|---------------|
| 07:00 + 13:00 | `SecondBrain-ClickUpSync` | `scripts/scheduled-sync.sh` | `scripts/register-scheduled-sync.ps1` |
| 19:00 | `SecondBrain-DailyReflection` | `scripts/daily-reflection.sh` | `scripts/register-daily-reflection.ps1` |
| 20:00 | `SecondBrain-DailyLinkVault` | `scripts/daily-link-vault.sh` | `scripts/register-daily-link-vault.ps1` |
| Mon–Fri 21:00 | `InsightAgent-DailyBlindSpots` | `scripts/insight-agent.py --lens blind-spots` | by hand (no ps1 yet) |
| Mon–Fri 21:15 | `ResearchAgent-DailyAfterInsight` | `scripts/research-agent.py` | by hand (no ps1 yet) |
| Mon 08:00 | `InsightAgent-WeeklyBrief` | `scripts/insight-agent.py --lens weekly` | by hand (no ps1 yet) |

- **scheduled-sync.sh** — 4 steps: ClickUp docs (`/sync-clickup`) → Linear (`/sync-linear`) → ClickUp chat (`scripts/sync-clickup-chat.py`) → re-index (QMD `embed` + LightRAG `POST /documents/scan`). All Claude calls use `claude-haiku-4-5-20251001`.
- **daily-reflection.sh** — step 0 runs `scripts/check-seam.py` (seam/config integrity, always runs), then reviews `~/.claude/daily-logs/{date}.md`. Claude Haiku writes the **proposed** curated MEMORY.md to a temp file and the script copies it to `~/.claude/MEMORY.md` + `<vault>/Tools/Config/MEMORY.md` itself — agent writes under `~/.claude` are permission-blocked in unattended runs, which silently broke this pipeline for weeks (Aug 2026) before propose-then-copy replaced agent-side edits.
- **daily-link-vault.sh** — runs `/link-vault --auto` scoped to ~120 linkable content files (skips chat snapshots, auto-backups, Linear snapshots, Library/Prompts/), then re-indexes QMD.

## Intelligence Loop (Phase 7)

Two-stage nightly pipeline that reads the vault and produces actionable analysis.

### Stage 1 — Insight Agent (`scripts/insight-agent.py`)

Reads ~120K chars from session notes, daily logs, MEMORY.md, product docs (via `~/.claude/projects/.../product-mentor/memory/`), Linear snapshots, ClickUp chat snapshots, and previous insights. Runs one of three lenses via the Anthropic Claude API:

- `blind-spots` (default, 21:00) — attention gaps, assumption risks, neglected products, stale threads
- `patterns` — cross-product themes, repeated decisions, convergence opportunities
- `weekly` (Mon 08:00) — exec brief with 🟢/🟡/🔴 scorecard per product

Output: `<vault>/Work/Insights/{date}-{lens}.md` + summary posted to ClickUp channel `your-channel-id-here` (configured via env).

### Stage 2 — Research Agent (`scripts/research-agent.py`)

Reads the latest insight report. Uses Claude to extract top 3 research topics. Fetches live web data via **Gemini 2.5 Flash** (Claude fallback if Gemini key absent). Synthesizes a structured brief per topic (what's happening / best practices / recommended actions / signals to watch).

Output: `<vault>/Work/Research/{date}-research.md` + summary posted to the same ClickUp channel.

### Manual invocation

```bash
CLAUDE_SILENT_STOP=1 python3 scripts/insight-agent.py --lens blind-spots
CLAUDE_SILENT_STOP=1 python3 scripts/insight-agent.py --lens weekly
CLAUDE_SILENT_STOP=1 python3 scripts/insight-agent.py --dry-run   # preview context only
CLAUDE_SILENT_STOP=1 python3 scripts/research-agent.py
CLAUDE_SILENT_STOP=1 python3 scripts/research-agent.py --topic "SLA breach playbook"
```

`CLAUDE_SILENT_STOP=1` prevents the SessionEnd hook from interfering with the Claude CLI calls these agents make internally.

## Chat Sync (Two-Phase Architecture)

ClickUp chat sync uses two distinct phases to keep Haiku context small and conversion deterministic:

| Phase | Script | What it does |
|-------|--------|--------------|
| **Fetch** | `scripts/sync-clickup-chat.py` | Pulls 33 channels × last 25 msgs via ClickUp MCP — outputs raw JSON |
| **Convert** | `scripts/convert-chat-json.py` | Parses raw JSON into Obsidian markdown snapshots — pure Python, no LLM cost |

Two on-demand utilities:
- `scripts/chat-snapshot.py` — point-in-time snapshot of a single channel
- `scripts/sync-chat-now.py` — manual one-shot sync without the scheduler

The fast path is what `scheduled-sync.sh` step 3 invokes.

## Global Config

Four global files in `~/.claude/`, loaded in every session of every project:

| File | Purpose | Updated by |
|------|---------|------------|
| `~/.claude/CLAUDE.md` | Orchestrator — loads the other 3 files, defines update rules | Manual edit |
| `~/.claude/USER.md` | User profile — role, teams, tools, preferences | Claude (when it learns new info) |
| `~/.claude/SOUL.md` | Behavior — communication style, guardrails, Linear ticket conventions | Manual edit (only when user asks) |
| `~/.claude/MEMORY.md` | Curated knowledge — decisions, initiatives, lessons learned | Claude (on important decisions) + daily reflection at 19:00 |

All four are synced to `<vault>/Tools/` by the SessionEnd hook on every session close.

**Hard boundaries live in the permission layer, not in markdown.** Each profile's `~/.claude*/settings.json` carries `permissions.deny`/`ask` rules (added 2026-08-19): deny `Read` of `.env`, `.env.*`, `*.local.json`, `*.usermap.json`, `.credentials.json`; deny direct `git push --force`/`-f` (deny beats the broad `Bash(git:*)` allow; the sanctioned force-push path `build-public-snapshot.sh` is unaffected since rules match the typed command, not script internals); `git filter-repo` requires confirmation. Known limitations: prefix rules miss trailing flags (`git push origin main --force`) and shell-level reads (`cat .env`) — a dedicated PreToolUse hook would be the robust version.

## Session Close

- `/end-session` runs `/log` + `/save-session`, then user presses Ctrl+C (triggers SessionEnd hook).
- Quick close: just Ctrl+C — auto-backup only.

## Scripts Reference

| Script | Type | Triggered by |
|--------|------|--------------|
| `install.sh` | Setup | one-shot — deploys commands + registers hooks + installs git pre-commit guard |
| `check-repo-safe.sh` | Guard | `.git/hooks/pre-commit` (installed by `install.sh`); also `--tree <dir>` mode used by `build-public-snapshot.sh` |
| `build-public-snapshot.sh` | Manual | on-demand — rebuilds and force-pushes the sanitized `public` remote from `scripts/repo-safety.config.json` |
| `setup-qmd.sh` | Setup | one-shot — installs QMD, registers vault collection, runs embed |
| `setup-lightrag.sh` | Setup | one-shot — starts Docker service, builds initial index |
| `session-backup.py` | Hook | `SessionEnd` event |
| `pre-compact.py` | Hook | `PreCompact` event |
| `scheduled-sync.sh` | Scheduler | 07:00, 13:00 |
| `daily-reflection.sh` | Scheduler | 19:00 |
| `check-seam.py` | Integrity | step 0 of `daily-reflection.sh`; manual: `py scripts/check-seam.py` |
| `daily-link-vault.sh` | Scheduler | 20:00 |
| `insight-agent.py` | Scheduler | Mon–Fri 21:00, Mon 08:00 |
| `research-agent.py` | Scheduler | Mon–Fri 21:15 |
| `sync-clickup-chat.py` | Sync | called by `scheduled-sync.sh` |
| `convert-chat-json.py` | Sync | called downstream of chat fetch |
| `sync-chat-now.py` | Manual | on-demand chat sync |
| `chat-snapshot.py` | Manual | single-channel snapshot |
| `register-scheduled-sync.ps1` | Win setup | registers `SecondBrain-ClickUpSync` |
| `register-daily-reflection.ps1` | Win setup | registers `SecondBrain-DailyReflection` |
| `register-daily-link-vault.ps1` | Win setup | registers `SecondBrain-DailyLinkVault` |
