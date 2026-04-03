# Session Auto-Backup — Design Spec

**Date:** 2026-04-03
**Status:** Approved
**Goal:** Automatically save a lightweight backup of every non-trivial Claude Code session to the Obsidian vault, as a safety net complementing the manual `/save-session` command.

---

## Problem

Users forget to run `/save-session` and lose session context. The manual command produces high-quality structured notes, but only when remembered. There is no safety net for sessions that end without saving.

## Solution

A `SessionEnd` hook runs a Python script that extracts user messages from the session transcript and writes a lightweight markdown note to the vault. This runs globally (all projects, all sessions) with a minimum-message filter to skip trivial sessions.

## Two-Layer Model

| Layer | Trigger | Quality | Purpose |
|-------|---------|---------|---------|
| **Auto-backup** (this spec) | Every session close | Lightweight — user messages + metadata | Safety net, never lose context |
| **`/save-session`** (existing) | Manual | Rich — decisions, outcomes, wikilinks, insights | Structured reference notes |

Both coexist. Auto-backup ensures nothing is lost. `/save-session` produces polished notes when the user wants them.

---

## Components

### 1. Python script: `scripts/session-backup.py`

**Input:** JSON on stdin (provided by Claude Code hooks system):

```json
{
  "session_id": "c3df0532-01dd-4307-85fb-66d12f3cce7d",
  "transcript_path": "/path/to/transcript.jsonl",
  "cwd": "/c/Users/alexg/Documents/Projects/second-brain",
  "project_dir": "/c/Users/alexg/Documents/Projects/second-brain",
  "session_exit_reason": "other"
}
```

**Logic:**

1. Read JSON from stdin
2. Read the `.jsonl` transcript file (UTF-8)
3. Count messages where `type == "user"` — if < 3, exit silently (trivial session)
4. Extract all user message text content (skip system reminders, tool results)
5. Derive project name from `cwd` (last path component)
6. Resolve vault path: `VAULT_ROOT` env var, fallback `$HOME/Documents/Vaults/Mex_Vault`
7. Write markdown file to `<vault>/Work/Claude Code/Sessions/auto/<date>-<project>-<session_id_short>.md`
8. Exit 0

**Filtering user messages:**

Each JSONL line is a JSON object. User messages have `"type": "user"`. The message content can be:
- A string (simple text)
- A list of content blocks (each with `"type": "text"` and `"text": "..."`)

The script extracts text from both formats. It skips content that starts with `<` (system reminders injected into user turns).

**Error handling:**

- If transcript file doesn't exist or is unreadable: exit 0 silently (don't block session close)
- If vault root doesn't exist: exit 0 silently
- If markdown write fails: exit 0 silently (best-effort, never block)
- All errors go to stderr, never stdout

### 2. Hook configuration

**Location:** `~/.claude/settings.json` (global — all sessions, all projects)

```json
{
  "hooks": {
    "SessionEnd": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 \"$HOME/Documents/Projects/second-brain/scripts/session-backup.py\"",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
```

**Note:** The `install.sh` script will add this hook to the user's settings, merging with any existing hooks configuration. It will NOT overwrite other hooks.

### 3. Output format

**File path:** `<vault>/Work/Claude Code/Sessions/auto/YYYY-MM-DD-<project>-<session_id_first_8>.md`

**Content:**

```markdown
---
type: session-auto
date: YYYY-MM-DD
project: <project-name>
session_id: <full-session-id>
project_path: "<cwd as Windows path>"
messages: <count of user messages>
exit_reason: <session_exit_reason>
---

# Auto-backup: <project-name>

## User messages
- <first user message, truncated to 200 chars>
- <second user message, truncated to 200 chars>
- ...

## Resume
```powershell
cd "<project_path>"; claude --resume <session_id>
```

**Decisions:**

| Decision | Rationale |
|---------|-----------|
| `auto/` subfolder | Separates from structured `/save-session` notes |
| Type `session-auto` | Distinguishable in `/vault --type` filtering |
| Only user messages | Claude responses are too long; questions provide enough context for search |
| Truncate to 200 chars | Some messages are very long (pasted code); truncation keeps notes scannable |
| Session ID first 8 chars in filename | Prevents collision, keeps filenames short |
| Full session ID in frontmatter | Allows exact resume and dedup detection |
| Windows path in `project_path` | Matches `/save-session` convention for PowerShell resume commands |
| Timeout 15s | Script is I/O-bound (read JSONL, write markdown), should complete in <2s |
| Exit 0 on all errors | Hook must never block session termination |
| Filter < 3 user messages | Skips greetings, quick lookups, aborted sessions |

---

## Installation

### install.sh additions

1. Create `auto/` directory in vault: `mkdir -p "$VAULT_ROOT/Work/Claude Code/Sessions/auto"`
2. Register the SessionEnd hook in `~/.claude/settings.json`:
   - Read existing settings
   - Merge the SessionEnd hook (don't overwrite existing hooks)
   - Write back
   - Use Python for JSON merge (jq may not be available on Windows)

### Uninstall

Remove the hook entry from `~/.claude/settings.json`. Auto-backup stops immediately. Existing backup notes remain in the vault.

---

## Integration with existing system

- **`/vault --type session-auto`** — lists all auto-backups
- **`/vault <keywords>`** — finds auto-backups by user message content
- **QMD** — indexes auto-backups automatically on next `qmd embed`
- **`/save-session`** — unchanged, continues producing structured notes
- **Type inference** in `commands/vault.md` — add `Work/Claude Code/Sessions/auto/` path prefix mapping to `session-auto` type

---

## Files to create/modify

| File | Action | What |
|------|--------|------|
| `scripts/session-backup.py` | Create | The backup script |
| `scripts/install.sh` | Modify | Add auto/ dir creation + hook registration |
| `commands/vault.md` | Modify | Add `session-auto` to type inference table |
| `docs/setup.md` | Modify | Document hook setup and how to disable |
| `docs/commands.md` | Modify | Document `session-auto` type |
| `docs/architecture.md` | Modify | Update Phase 3 status, add hook to architecture |
| `CLAUDE.md` | Modify | Add auto-backup section |
| `README.md` | Modify | Update Phase 3 status and description |
