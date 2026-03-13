# Setup Guide

## Prerequisites

- [Obsidian](https://obsidian.md/) installed and configured with a vault
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) CLI installed and authenticated
- (Optional) ClickUp MCP server connected in Claude settings — only needed for `/sync-clickup`

## Installation

### 1. Clone the repository

```bash
git clone <repo-url> ~/Projects/second-brain
cd ~/Projects/second-brain
```

### 2. Run the install script

```bash
bash scripts/install.sh
```

This will:
- Copy all slash commands to `~/.claude/commands/`
- Create vault directories (`ClickUp/`, `Claude Code/Sessions/`, `Claude Code/Tools/`) if vault exists
- Copy `sync-config.template.json` to the vault (only if no config exists)

### 3. Configure vault path (if non-default)

The default vault path is `$HOME/Documents/Vault`. To use a different location:

```bash
VAULT_ROOT=/path/to/your/vault bash scripts/install.sh
```

Note: The slash commands themselves have hardcoded paths (`C:\Users\alexg\Documents\Vault`). If your vault is elsewhere, update the paths in `commands/*.md` before installing.

## ClickUp Sync Configuration (Optional)

If you use ClickUp and want to sync documents to the vault:

1. Ensure the ClickUp MCP server is connected in Claude settings
2. Discover available documents:
   ```
   /sync-clickup --discover
   ```
3. Add documents to track:
   ```
   /sync-clickup --add <doc_id> "Document Name" "ClickUp/Category/Doc Name"
   ```
4. Run the sync:
   ```
   /sync-clickup
   ```

The sync config lives at `<vault_root>/ClickUp/sync-config.json`.

## Verification

After installation, verify everything works:

| Test | Command | Expected Result |
|------|---------|-----------------|
| Commands deployed | `ls ~/.claude/commands/vault.md` | File exists |
| Vault help | `/vault` | Shows file count and usage |
| Type listing | `/vault --types` | Shows types with counts |
| Keyword search | `/vault <any keyword>` | Returns matching files |
| Session save | `/save-session test` | Creates note in `Claude Code/Sessions/` |

## Updating Commands

After editing commands in the repository:

```bash
bash scripts/install.sh
```

The script is idempotent — it overwrites commands but never overwrites an existing `sync-config.json`.
