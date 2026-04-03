#!/usr/bin/env bash
# Daily link discovery — scan vault for new connections between documents
# Runs via Task Scheduler at 20:00 daily.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$HOME/.claude/daily-logs/sync.log"

echo "[$(date -Iseconds)] Starting daily link-vault scan..." >> "$LOG_FILE"

# Only scan content areas that benefit from linking (skip prompts, configs, chat, auto-backups)
claude -p "
Run /link-vault --auto but ONLY scan these folders:
- Work/ClickUp/ (product docs)
- Work/Claude Code/Sessions/ (session notes, NOT auto/)
- Work/EOD/ (end-of-day reports)
- Work/Search Atlas/
- Tools/USER.md, Tools/SOUL.md, Tools/MEMORY.md

Skip these entirely:
- Personal/AI/Prompts/ (self-contained templates)
- Work/ClickUp/Chat/ (snapshots, not linkable)
- Work/Claude Code/Sessions/auto/ (auto-backups, too noisy)
- Work/Linear/ (snapshots)
- Tools/CC/ (config docs)

This reduces the scan from ~482 files to ~120 linkable content files.
" --cwd "$REPO_ROOT" >> "$LOG_FILE" 2>&1

EXIT_CODE=$?
echo "[$(date -Iseconds)] Link-vault done (exit: $EXIT_CODE)" >> "$LOG_FILE"

# Re-index after new links are created
if command -v qmd &> /dev/null; then
  echo "[$(date -Iseconds)] Running QMD incremental index..." >> "$LOG_FILE"
  qmd embed >> "$LOG_FILE" 2>&1
  echo "[$(date -Iseconds)] QMD index done" >> "$LOG_FILE"
fi

exit $EXIT_CODE
