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
- Create vault directories (`Work/ClickUp/`, `Work/Claude Code/Sessions/`, `Tools/`) if vault exists
- Copy `sync-config.template.json` to the vault (only if no config exists)

### 3. Configure vault path (if non-default)

The default vault path is `$HOME/Documents/Vaults/Mex_Vault`. To use a different location:

```bash
VAULT_ROOT=/path/to/your/vault bash scripts/install.sh
```

The install script substitutes `{{VAULT_ROOT}}` placeholders in all commands with the resolved path, so commands will point to your vault automatically.

## ClickUp Sync Configuration (Optional)

If you use ClickUp and want to sync documents to the vault:

1. Ensure the ClickUp MCP server is connected in Claude settings
2. Discover available documents:
   ```
   /sync-clickup --discover
   ```
3. Add documents to track:
   ```
   /sync-clickup --add <doc_id> "Document Name" "Work/ClickUp/Category/Doc Name"
   ```
4. Run the sync:
   ```
   /sync-clickup
   ```

The sync config lives at `<vault_root>/Work/ClickUp/sync-config.json`.

### Scheduled sync (optional)

To keep ClickUp docs automatically updated, register a Windows Scheduled Task:

```powershell
# Run as Administrator (one-time setup)
powershell -ExecutionPolicy Bypass -File scripts\register-scheduled-sync.ps1
```

This syncs all tracked docs daily at 08:00 and re-indexes QMD. To change the schedule, edit the task in Task Scheduler or modify `scripts/register-scheduled-sync.ps1`.

To run manually: `bash scripts/scheduled-sync.sh`

Logs are written to `~/.claude/daily-logs/sync.log`.

## QMD Semantic Search (Optional)

QMD adds hybrid search (BM25 + vector embeddings + LLM re-ranking) to `/vault`. Without QMD, search falls back to Grep/Glob keyword matching.

### Prerequisites

- Node.js >= 22 (`node -v` to check)
- ~2GB disk space for local models (downloaded to `~/.cache/qmd/models/`)

### 1. Run the QMD setup script

```bash
bash scripts/setup-qmd.sh
```

This will:
- Install QMD globally (`npm install -g @tobilu/qmd`)
- Register your vault as a QMD collection
- Add context metadata for each vault folder
- Run initial embedding (~1-2 minutes for <1000 files)

### 2. Register QMD MCP server in Claude Code

Add to your Claude Code settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "qmd": {
      "command": "qmd",
      "args": ["mcp"]
    }
  }
}
```

For faster subsequent queries, use the persistent HTTP server instead:

```json
{
  "mcpServers": {
    "qmd": {
      "type": "http",
      "url": "http://localhost:8181/mcp"
    }
  }
}
```

Then start the QMD daemon: `qmd mcp --http --daemon`

### 3. Verify

In a new Claude Code session:

| Test | How | Expected Result |
|------|-----|-----------------|
| MCP connected | Claude has `query` tool available | Tool appears in MCP tools list |
| Search works | `/vault reliability plan` | Results with semantic matches, not just keyword hits |
| Fallback works | Disconnect QMD MCP, run `/vault test` | Falls back to Grep/Glob silently |

### Updating embeddings

After adding or modifying vault files, re-run embeddings:

```bash
qmd embed
```

Or force a full re-index:

```bash
qmd embed -f
```

## Session Auto-Backup (Hook)

Every non-trivial Claude Code session is automatically saved to the vault when it ends. This is configured as a global SessionEnd hook by `install.sh`.

### How it works

1. When you close a Claude Code session **gracefully**, the hook runs `scripts/session-backup.py`
2. The script reads the session transcript, extracts your messages, and writes a markdown note
3. Sessions with fewer than 3 messages are skipped (greetings, quick lookups)
4. Notes go to `<vault>/Work/Claude Code/Sessions/auto/`

### Important: close sessions gracefully

The hook only runs if Claude Code has time to execute it. Use `/exit` or `Ctrl+C` to close sessions — **do not** close the terminal window directly (clicking X), as this kills the process before the hook can run.

| How you close | Hook runs? |
|---------------|-----------|
| `/exit` | Yes |
| `Ctrl+C` | Yes |
| Close terminal window (X) | No |

### Disabling auto-backup

Remove the `SessionEnd` entry from `~/.claude/settings.json`:

```json
{
  "hooks": {
    "SessionEnd": []
  }
}
```

Or delete the `"SessionEnd"` key entirely.

### Verifying it works

After closing a session with 3+ messages, check:

```bash
ls "$HOME/Documents/Vaults/Mex_Vault/Work/Claude Code/Sessions/auto/"
```

You should see a file like `2026-04-03-my-project-c3df0532.md`.

### Closing sessions

| Action | What happens |
|--------|-------------|
| `Ctrl+C` or `/exit` | Session closes, auto-backup hook saves lightweight note |
| `/end-session` then `Ctrl+C` | Full save (/log + /save-session + auto-backup) |
| Close window (X button) | No hook fires — context lost |

**Recommended:** Use `/end-session` for important sessions, `Ctrl+C` for quick ones. Never close the window directly.

### Global user profile

`install.sh` does NOT create the global config files. These are created once manually:

- `~/.claude/CLAUDE.md` — Global instructions for all sessions
- `~/.claude/USER.md` — Your profile (role, teams, tools)

The session-backup hook syncs `USER.md` to `<vault>/Tools/USER.md` on every session close, keeping the Obsidian copy up to date.

## Verification

After installation, verify everything works:

| Test | Command | Expected Result |
|------|---------|-----------------|
| Commands deployed | `ls ~/.claude/commands/vault.md` | File exists |
| Vault help | `/vault` | Shows file count and usage |
| Type listing | `/vault --types` | Shows types with counts |
| Keyword search | `/vault <any keyword>` | Returns matching files |
| Session save | `/save-session test` | Creates note in `Work/Claude Code/Sessions/` |

## Updating Commands

After editing commands in the repository:

```bash
bash scripts/install.sh
```

The script is idempotent — it overwrites commands but never overwrites an existing `sync-config.json`.
