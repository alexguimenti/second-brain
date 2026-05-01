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
#   Trigger: Daily at 07:00

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_ROOT="${VAULT_ROOT:-$HOME/Documents/Vaults/Mex_Vault}"
LOG_FILE="$HOME/.claude/daily-logs/sync.log"

# Log to both terminal and file
log() { echo "$1" | tee -a "$LOG_FILE"; }

log ""
log "════════════════════════════════════════"
log "  Second Brain Sync — $(date '+%Y-%m-%d %H:%M:%S')"
log "════════════════════════════════════════"

if [[ "${1:-}" == "--dry-run" ]]; then
  log "[DRY RUN] Would run: /sync-clickup, /sync-linear, sync-clickup-chat.py"
  exit 0
fi

# All claude commands must run from the repo root so skills resolve correctly
cd "$REPO_ROOT"

# ── 1. ClickUp docs ──────────────────────────────────────────────────────────
log ""
log "▶ [1/4] Syncing ClickUp docs..."
claude --model claude-haiku-4-5-20251001 -p "/sync-clickup" 2>&1 | tee -a "$LOG_FILE"
log "✓ [1/4] ClickUp docs done ($(date '+%H:%M:%S'))"

# ── 2. Linear ────────────────────────────────────────────────────────────────
log ""
log "▶ [2/4] Syncing Linear..."
claude --model claude-haiku-4-5-20251001 -p "/sync-linear" 2>&1 | tee -a "$LOG_FILE"
log "✓ [2/4] Linear done ($(date '+%H:%M:%S'))"

# ── 3. ClickUp chat channels ─────────────────────────────────────────────────
CHAT_CONFIG="$VAULT_ROOT/Work/ClickUp/chat-sync-config.json"
if [ -f "$CHAT_CONFIG" ]; then
  if [ -f "$HOME/.workbench.env" ]; then
    set -a; source "$HOME/.workbench.env"; set +a
  fi
  log ""
  log "▶ [3/4] Syncing ClickUp chat (33 channels, last 25 msgs each)..."
  python3 "$SCRIPT_DIR/sync-clickup-chat.py" 2>&1 | tee -a "$LOG_FILE"
  EXIT_CODE="${PIPESTATUS[0]}"
  log "✓ [3/4] Chat done ($(date '+%H:%M:%S'))"
else
  EXIT_CODE=0
  log "- [3/4] Chat skipped (no config)"
fi

# ── 4. Re-index ──────────────────────────────────────────────────────────────
log ""
log "▶ [4/4] Re-indexing..."

if command -v qmd &> /dev/null; then
  log "  → QMD incremental index..."
  qmd embed 2>&1 | tee -a "$LOG_FILE"
  log "  ✓ QMD done"
else
  log "  - QMD not available, skipping"
fi

if curl -s http://localhost:9621/health > /dev/null 2>&1; then
  log "  → LightRAG re-index..."
  LIGHTRAG_INPUTS="$REPO_ROOT/lightrag/data/inputs"
  rm -f "$LIGHTRAG_INPUTS"/*.md 2>/dev/null

  find "$VAULT_ROOT/Work/ClickUp" -name "*.md" -not -path "*/Chat/*" -exec cp {} "$LIGHTRAG_INPUTS/" \; 2>/dev/null
  find "$VAULT_ROOT/Work/Claude Code/Sessions" -name "*.md" -not -path "*/auto/*" -exec cp {} "$LIGHTRAG_INPUTS/" \; 2>/dev/null
  find "$VAULT_ROOT/Work/EOD" -name "*.md" -exec cp {} "$LIGHTRAG_INPUTS/" \; 2>/dev/null
  find "$VAULT_ROOT/Work/Search Atlas" -name "*.md" -exec cp {} "$LIGHTRAG_INPUTS/" \; 2>/dev/null

  curl -s -X POST http://localhost:9621/documents/scan 2>&1 | tee -a "$LOG_FILE"
  log "  ✓ LightRAG triggered"
else
  log "  - LightRAG not running, skipping"
fi

log ""
log "════════════════════════════════════════"
log "  Sync complete — $(date '+%H:%M:%S')"
log "════════════════════════════════════════"
log ""

exit $EXIT_CODE
