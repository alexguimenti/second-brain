#!/usr/bin/env bash
# Daily Reflection — review today's daily log and update MEMORY.md
# Runs via Task Scheduler at 19:00 daily.
#
# What it does:
# 1. Reads today's daily log (~/.claude/daily-logs/YYYY-MM-DD.md)
# 2. Asks Claude to identify important decisions, initiatives, and lessons
# 3. Updates ~/.claude/MEMORY.md with promoted items and removes stale entries
# 4. Syncs MEMORY.md to the vault

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_ROOT="${VAULT_ROOT:-$HOME/Documents/Vaults/Mex_Vault}"
LOG_FILE="$HOME/.claude/daily-logs/sync.log"
TODAY=$(date +%Y-%m-%d)
DAILY_LOG="$VAULT_ROOT/Work/Claude Code/Daily Logs/$TODAY.md"

# Log to both terminal and file
log() { echo "$1" | tee -a "$LOG_FILE"; }

log ""
log "════════════════════════════════════════"
log "  Daily Reflection — $TODAY $(date '+%H:%M:%S')"
log "════════════════════════════════════════"

# Skip if no daily log exists for today
if [ ! -f "$DAILY_LOG" ]; then
  log "- No daily log for $TODAY, skipping"
  exit 0
fi

log "▶ Reading daily log + updating MEMORY.md..."

# Run reflection from repo root so skills resolve correctly
cd "$REPO_ROOT"

# Run reflection via Claude Code
claude --model claude-haiku-4-5-20251001 -p "
You have access to two files:
1. Today's daily log: ~/.claude/daily-logs/$TODAY.md
2. The current MEMORY.md: ~/.claude/MEMORY.md

Read both files. Then update MEMORY.md following these rules:

**Add** to the appropriate section:
- New important decisions (with date) → Recent Decisions
- New initiatives or status changes → Active Initiatives
- Product status updates → Product Status
- New lessons or patterns discovered → Lessons Learned

**Remove** from MEMORY.md:
- Decisions older than 2 weeks that are no longer relevant
- Initiatives that have been completed or cancelled
- Product status that has been superseded by newer info

**Keep** MEMORY.md concise — under 60 lines. This is working memory, not a log.

After updating, copy MEMORY.md to the vault: copy ~/.claude/MEMORY.md to ~/Documents/Vaults/Mex_Vault/Tools/MEMORY.md

Report what you added and removed.
" 2>&1 | tee -a "$LOG_FILE"

EXIT_CODE="${PIPESTATUS[0]}"
log "✓ Daily reflection done ($(date '+%H:%M:%S'), exit: $EXIT_CODE)"

exit $EXIT_CODE
