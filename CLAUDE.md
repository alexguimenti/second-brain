# Second Brain

Canonical source for the Second Brain knowledge management tooling — Obsidian vault integration, Claude Code slash commands, and ClickUp document sync.

## Key Paths

- **Vault root:** `$HOME/Documents/Vault` (Obsidian vault, not in this repo)
- **Commands deployment target:** `~/.claude/commands/`
- **Sync config (live):** `<vault_root>/ClickUp/sync-config.json`

## Conventions

- **Prompt-as-code:** Slash commands are markdown files that Claude Code interprets as instructions. Treat them as source code — version, review, test.
- **Hardcoded vault path:** Commands reference `C:\Users\alexg\Documents\Vault` directly. Override via `VAULT_ROOT` env var in `scripts/install.sh` for other machines.
- **Language:** English for all documentation and command prompts.
- **No personal data:** The `config/sync-config.template.json` uses placeholder IDs. Never commit real ClickUp document IDs or tokens.

## Workflow

1. Edit commands in `commands/`
2. Run `bash scripts/install.sh` to deploy
3. Test in a Claude Code session (e.g., `/vault --types`, `/sync-clickup --discover`)
