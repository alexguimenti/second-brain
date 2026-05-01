#!/usr/bin/env bash
# Daily link discovery — scan vault for new connections between documents
# Runs via Task Scheduler at 20:00 daily.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="$HOME/.claude/daily-logs/sync.log"

# Log to both terminal and file
log() { echo "$1" | tee -a "$LOG_FILE"; }

log ""
log "════════════════════════════════════════"
log "  Daily Link Vault — $(date '+%Y-%m-%d %H:%M:%S')"
log "════════════════════════════════════════"
log "▶ Scanning ~120 vault files for new connections..."

cd "$REPO_ROOT"

claude --model claude-haiku-4-5-20251001 -p "
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
" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE="${PIPESTATUS[0]}"
log "✓ Link vault done ($(date '+%H:%M:%S'), exit: $EXIT_CODE)"

if command -v qmd &> /dev/null; then
  log "▶ Running QMD incremental index..."
  qmd embed 2>&1 | tee -a "$LOG_FILE"
  log "✓ QMD done"
fi

log ""

exit $EXIT_CODE
