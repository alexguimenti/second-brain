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
EXIT_CODE=$?
echo "[$(date -Iseconds)] Linear sync done (exit: $EXIT_CODE)" >> "$LOG_FILE"

# Re-index vault if QMD is available
if command -v qmd &> /dev/null; then
  echo "[$(date -Iseconds)] Running QMD incremental index..." >> "$LOG_FILE"
  qmd embed >> "$LOG_FILE" 2>&1
  echo "[$(date -Iseconds)] QMD index done" >> "$LOG_FILE"
fi

exit $EXIT_CODE
