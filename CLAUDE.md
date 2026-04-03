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
