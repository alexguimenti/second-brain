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
log "▶ Scanning vault for new connections (see .vaultignore for excluded paths)..."

cd "$REPO_ROOT"

# `set -euo pipefail` is active, so a non-zero exit from `claude` would abort the
# whole run right here -- before the exit code is even logged, and before the QMD
# embedding step below. That is backwards: the point of capturing PIPESTATUS is to
# record a failure and keep going. Disable errexit around the pipeline only, so the
# exit code is read and reported instead of killing the run.
set +e
claude --model claude-haiku-4-5-20251001 -p "
Run /link-vault --auto
" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE="${PIPESTATUS[0]}"
set -e

log "✓ Link vault done ($(date '+%H:%M:%S'), exit: $EXIT_CODE)"
if [ "$EXIT_CODE" -ne 0 ]; then
  log "⚠ /link-vault exited $EXIT_CODE — continuing to the remaining steps anyway"
fi

# Regenerate the inventory index (cheap: reads frontmatter, writes one file).
# The deep docs under Tools/Inventory/ are a drifting hand-made snapshot; this
# index is what keeps an accurate list of installed skills/commands.
INVENTORY_SCRIPT="${VAULT_ROOT:-$HOME/Documents/Vaults/MyVault}/Tools/Scripts/build-inventory-index.ps1"
if [ -f "$INVENTORY_SCRIPT" ] && command -v pwsh &> /dev/null; then
  log "▶ Regenerating inventory index..."
  # Non-fatal on purpose: `set -euo pipefail` is active, so without `|| true` a
  # non-zero exit here would abort the run before the QMD step below. The index
  # is cosmetic; the embedding is not.
  if pwsh -NoProfile -File "$INVENTORY_SCRIPT" 2>&1 | tee -a "$LOG_FILE"; then
    log "✓ Inventory index done"
  else
    log "⚠ Inventory index failed (continuing — QMD step still runs)"
  fi
fi

if command -v qmd &> /dev/null; then
  log "▶ Running QMD incremental index..."
  qmd embed 2>&1 | tee -a "$LOG_FILE"
  log "✓ QMD done"
fi

log ""

exit $EXIT_CODE
