#!/usr/bin/env bash
# Daily link discovery — scan vault for new connections between documents
# Runs via Task Scheduler at 20:00 daily.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$HOME/.claude/daily-logs/sync.log"

echo "[$(date -Iseconds)] Starting daily link-vault scan..." >> "$LOG_FILE"

claude -p "/link-vault --auto" --cwd "$REPO_ROOT" >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "[$(date -Iseconds)] Link-vault done (exit: $EXIT_CODE)" >> "$LOG_FILE"

# Re-index after new links are created
if command -v qmd &> /dev/null; then
  echo "[$(date -Iseconds)] Running QMD incremental index..." >> "$LOG_FILE"
  qmd embed >> "$LOG_FILE" 2>&1
  echo "[$(date -Iseconds)] QMD index done" >> "$LOG_FILE"
fi

exit $EXIT_CODE
