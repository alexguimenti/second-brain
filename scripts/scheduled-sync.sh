#!/usr/bin/env bash
# Scheduled ClickUp sync — run via Task Scheduler or cron
# Syncs all tracked ClickUp documents to the Obsidian vault.
#
# Usage:
#   bash scripts/scheduled-sync.sh           # sync all docs
#   bash scripts/scheduled-sync.sh --dry-run # just show what would sync
#
# Schedule (Windows Task Scheduler):
#   Action: bash
#   Arguments: "C:\Users\...\second-brain\scripts\scheduled-sync.sh"
#   Trigger: Daily at 08:00 (or your preferred time)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_ROOT="${VAULT_ROOT:-$HOME/Documents/Vaults/Mex_Vault}"
LOG_FILE="$HOME/.claude/daily-logs/sync.log"

echo "[$(date -Iseconds)] Starting scheduled sync..." >> "$LOG_FILE"

if [[ "${1:-}" == "--dry-run" ]]; then
  echo "[DRY RUN] Would run: claude -p /sync-clickup --cwd $REPO_ROOT"
  exit 0
fi

# Run sync-clickup via Claude Code non-interactive mode
claude -p "/sync-clickup" --cwd "$REPO_ROOT" >> "$LOG_FILE" 2>&1
echo "[$(date -Iseconds)] ClickUp sync done (exit: $?)" >> "$LOG_FILE"

# Run sync-linear
claude -p "/sync-linear" --cwd "$REPO_ROOT" >> "$LOG_FILE" 2>&1
echo "[$(date -Iseconds)] Linear sync done (exit: $?)" >> "$LOG_FILE"

# Run sync-clickup-chat (if config exists)
CHAT_CONFIG="$VAULT_ROOT/Work/ClickUp/chat-sync-config.json"
if [ -f "$CHAT_CONFIG" ]; then
  claude -p "/sync-clickup-chat" --cwd "$REPO_ROOT" >> "$LOG_FILE" 2>&1
  EXIT_CODE=$?
  echo "[$(date -Iseconds)] ClickUp chat sync done (exit: $EXIT_CODE)" >> "$LOG_FILE"
else
  EXIT_CODE=0
  echo "[$(date -Iseconds)] ClickUp chat sync skipped (no config)" >> "$LOG_FILE"
fi

# Re-index vault if QMD is available
if command -v qmd &> /dev/null; then
  echo "[$(date -Iseconds)] Running QMD incremental index..." >> "$LOG_FILE"
  qmd embed >> "$LOG_FILE" 2>&1
  echo "[$(date -Iseconds)] QMD index done" >> "$LOG_FILE"
fi

# Re-index LightRAG if running
if curl -s http://localhost:9621/health > /dev/null 2>&1; then
  echo "[$(date -Iseconds)] Syncing vault files to LightRAG..." >> "$LOG_FILE"
  LIGHTRAG_INPUTS="$REPO_ROOT/lightrag/data/inputs"
  rm -f "$LIGHTRAG_INPUTS"/*.md 2>/dev/null

  find "$VAULT_ROOT/Work/ClickUp" -name "*.md" -not -path "*/Chat/*" -exec cp {} "$LIGHTRAG_INPUTS/" \; 2>/dev/null
  find "$VAULT_ROOT/Work/Claude Code/Sessions" -name "*.md" -not -path "*/auto/*" -exec cp {} "$LIGHTRAG_INPUTS/" \; 2>/dev/null
  find "$VAULT_ROOT/Work/EOD" -name "*.md" -exec cp {} "$LIGHTRAG_INPUTS/" \; 2>/dev/null
  find "$VAULT_ROOT/Work/Search Atlas" -name "*.md" -exec cp {} "$LIGHTRAG_INPUTS/" \; 2>/dev/null

  curl -s -X POST http://localhost:9621/documents/scan >> "$LOG_FILE" 2>&1
  echo "[$(date -Iseconds)] LightRAG re-index triggered" >> "$LOG_FILE"
else
  echo "[$(date -Iseconds)] LightRAG not running, skipping" >> "$LOG_FILE"
fi

exit $EXIT_CODE
