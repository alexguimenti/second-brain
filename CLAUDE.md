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
- **Daily log:** Also appends a session summary to `~/.claude/daily-logs/YYYY-MM-DD.md` (feeds into `/eod`)
- **Filter:** Sessions with < 3 user messages are skipped
- **Scope:** Global — runs on all sessions in all projects
- **Type:** `session-auto` (distinct from `session` created by `/save-session`)
- **Script:** `scripts/session-backup.py` — registered as hook via `install.sh`

## Global Config

Three global files in `~/.claude/`, loaded in every session of every project:

| File | Purpose | Updated by |
|------|---------|------------|
| `~/.claude/CLAUDE.md` | Orchestrator — loads USER.md and SOUL.md, defines update rules | Manual edit |
| `~/.claude/USER.md` | User profile — role, teams, tools, preferences | Claude (when it learns new info) |
| `~/.claude/SOUL.md` | Behavior — communication style, guardrails, Linear ticket conventions | Manual edit (only when user asks) |

All three are synced to `<vault>/Tools/` by the session-backup hook on every session close.

- **Session close:** `/end-session` runs /log + /save-session, then user presses Ctrl+C (triggers auto-backup hook)
