# Second Brain

Canonical source for the Second Brain knowledge management tooling — Obsidian vault integration, Claude Code slash commands, and ClickUp document sync.

## Key Paths

- **Vault root:** `$HOME/Documents/Vaults/Mex_Vault` (Obsidian vault, not in this repo)
- **Commands deployment target:** `~/.claude/commands/`
- **Sync config (live):** `<vault_root>/Work/ClickUp/sync-config.json`
- **QMD config:** `~/.config/qmd/index.yml` (QMD collection and context config)
- **QMD cache:** `~/.cache/qmd/` (SQLite index + local models)

## Conventions

- **Prompt-as-code:** Slash commands are markdown files that Claude Code interprets as instructions. Treat them as source code — version, review, test.
- **Vault path via template:** Commands use `{{VAULT_ROOT}}` placeholder. `install.sh` substitutes it with the resolved `VAULT_ROOT` env var (default: `$HOME/Documents/Vaults/Mex_Vault`).
- **Language:** English for all documentation and command prompts.
- **No personal data:** The `config/sync-config.template.json` uses placeholder IDs. Never commit real ClickUp document IDs or tokens.

## Workflow

1. Edit commands in `commands/`
2. Run `bash scripts/install.sh` to deploy
3. Test in a Claude Code session (e.g., `/vault --types`, `/sync-clickup --discover`)

## QMD Integration

- **Scope:** QMD MCP is registered globally in `~/.claude.json` — available in **every** Claude Code session, not just this project
- **Implicit access:** Claude can search the vault automatically via `query`/`get` tools without explicit `/vault` calls
- **Explicit access:** `/vault` command uses QMD as preferred backend, falls back to Grep/Glob
- **Setup:** `bash scripts/setup-qmd.sh` installs QMD, registers vault, runs embedding
- **MCP config:** Registered in `~/.claude.json` (global) under `mcpServers.qmd` — see `docs/setup.md`
- **Re-index after vault changes:** `qmd embed` (incremental) or `qmd embed -f` (full)

## Auto-Backup Hook

- **What:** SessionEnd hook saves a lightweight backup of every non-trivial session to the vault
- **Where:** `<vault>/Work/Claude Code/Sessions/auto/`
- **Daily log:** Also appends a session summary to `<vault>/Work/Claude Code/Daily Logs/YYYY-MM-DD.md` (feeds into `/eod`)
- **Filter:** Sessions with < 3 user messages are skipped
- **Scope:** Global — runs on all sessions in all projects
- **Type:** `session-auto` (distinct from `session` created by `/save-session`)
- **Script:** `scripts/session-backup.py` — registered as hook via `install.sh`

## Global Config

Four global files in `~/.claude/`, loaded in every session of every project:

| File | Purpose | Updated by |
|------|---------|------------|
| `~/.claude/CLAUDE.md` | Orchestrator — loads the other 3 files, defines update rules | Manual edit |
| `~/.claude/USER.md` | User profile — role, teams, tools, preferences | Claude (when it learns new info) |
| `~/.claude/SOUL.md` | Behavior — communication style, guardrails, Linear ticket conventions | Manual edit (only when user asks) |
| `~/.claude/MEMORY.md` | Curated knowledge — decisions, initiatives, lessons learned | Claude (on important decisions) + daily reflection at 19:00 |

All four are synced to `<vault>/Tools/` by the session-backup hook on every session close.

## Hooks

| Hook | Event | Script | What it does |
|------|-------|--------|-------------|
| Session backup | `SessionEnd` | `scripts/session-backup.py` | Auto-backup + daily log + sync global files |
| Pre-compact | `PreCompact` | `scripts/pre-compact.py` | Extracts topics/decisions before context truncation |

## Scheduled Tasks

| Task | Schedule | Script | What it does |
|------|----------|--------|-------------|
| Sync | 07:00 + 13:00 | `scripts/scheduled-sync.sh` | ClickUp docs + Linear tickets + ClickUp chat + QMD re-index |
| Daily reflection | 19:00 | `scripts/daily-reflection.sh` | Reviews daily log, curates MEMORY.md |

## Session Close

- `/end-session` runs /log + /save-session, then user presses Ctrl+C (triggers auto-backup hook)
- Quick close: just Ctrl+C (auto-backup only)
