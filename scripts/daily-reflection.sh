#!/usr/bin/env bash
# Daily Reflection — review today's daily log and update MEMORY.md
# Runs via Task Scheduler at 19:00 daily.
#
# What it does:
# 0. Runs the seam integrity check (check-seam.py) — always, even on quiet days
# 1. Reads today's daily log (~/.claude/daily-logs/YYYY-MM-DD.md)
# 2. Asks Claude to curate MEMORY.md and write the PROPOSAL to a temp file
# 3. Copies the proposal to ~/.claude/MEMORY.md + the vault — done by the script,
#    not the agent: agent writes under ~/.claude are blocked by the permission
#    system in unattended runs (sync.log, Aug 2026: weeks of "May I proceed with
#    the edit?", exit 0, nothing changed)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_ROOT="${VAULT_ROOT:-$HOME/Documents/Vaults/MyVault}"
LOG_FILE="$HOME/.claude/daily-logs/sync.log"
TODAY=$(date +%Y-%m-%d)
DAILY_LOG="$VAULT_ROOT/Work/Claude Code/Daily Logs/$TODAY.md"

# Log to both terminal and file
log() { echo "$1" | tee -a "$LOG_FILE"; }

log ""
log "════════════════════════════════════════"
log "  Daily Reflection — $TODAY $(date '+%H:%M:%S')"
log "════════════════════════════════════════"

# Step 0 — seam integrity check. Runs even on days with no daily log: config drift
# is silent, so a quiet day is exactly when a broken pointer would go unnoticed.
# Wrapped in set +e like the claude call below — a FAIL must be reported, not fatal.
log "▶ Seam integrity check..."
set +e
py "$REPO_ROOT/scripts/check-seam.py" 2>&1 | tee -a "$LOG_FILE"
SEAM_EXIT="${PIPESTATUS[0]}"
set -e
if [ "$SEAM_EXIT" -ne 0 ]; then
  log "⚠ Seam check FAILED (exit $SEAM_EXIT) — details above"
fi

# Skip if no daily log exists for today
if [ ! -f "$DAILY_LOG" ]; then
  log "- No daily log for $TODAY, skipping"
  exit $SEAM_EXIT
fi

log "▶ Reading daily log + updating MEMORY.md..."

# The ONE destination this job is allowed to write in the vault. Named here rather
# than described in prose because the prompt used to say "copy MEMORY.md to the vault"
# and the model repeatedly dropped CLAUDE.md/MEMORY.md/SOUL.md into Tools/ root instead.
VAULT_MEMORY="${VAULT_ROOT:-$HOME/Documents/Vaults/MyVault}/Tools/Config/MEMORY.md"

# Where the agent writes its proposed MEMORY.md (gitignored tmp_*). Cleared
# before every run — a stale proposal from a failed run must never be applied.
PROPOSED="$REPO_ROOT/tmp_memory_proposed.md"
rm -f "$PROPOSED"

# Run reflection from repo root so skills resolve correctly
cd "$REPO_ROOT"

# Run reflection via Claude Code.
# `set -euo pipefail` is active, so a non-zero exit from `claude` would abort the run
# right here — before the exit code is logged at all. Disable errexit around this one
# pipeline so the failure is read and reported instead of vanishing.
set +e
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

**Resolve contradictions** — if a new item conflicts with an existing entry (a
decision reversing an earlier one, a status that changed), REPLACE the old entry;
never let both stand. Say so explicitly in your report.

**Demote detail** — MEMORY.md holds pointers, not documentation. If an entry grows
past ~2 lines of operational detail, keep the one-line summary + date and note in
your report which vault note should hold the detail. Do NOT create or edit any
vault file — your output goes to the temp file named below.

**Keep** MEMORY.md concise — under 60 lines. This is working memory, not a log.

Write the COMPLETE updated MEMORY.md content to EXACTLY this file, and no other:

  $PROPOSED

Do NOT edit ~/.claude/MEMORY.md yourself — the permission system blocks writes
under ~/.claude in unattended runs, and the run then silently changes nothing.
Do NOT write to the vault either. After you finish, this script copies your
proposal to ~/.claude/MEMORY.md and to $VAULT_MEMORY itself.

Report what you added, removed, and which contradictions you resolved.
" 2>&1 | tee -a "$LOG_FILE"
EXIT_CODE="${PIPESTATUS[0]}"
set -e

if [ "$EXIT_CODE" -eq 0 ] && [ -s "$PROPOSED" ]; then
  cp "$PROPOSED" "$HOME/.claude/MEMORY.md"
  cp "$PROPOSED" "$VAULT_MEMORY"
  rm -f "$PROPOSED"
  log "✓ Proposal applied: ~/.claude/MEMORY.md + vault updated"
else
  log "❌ No usable proposal (claude exit: $EXIT_CODE, file: $PROPOSED) — MEMORY.md untouched"
  EXIT_CODE=1
fi

log "✓ Daily reflection done ($(date '+%H:%M:%S'), exit: $EXIT_CODE)"

if [ "$EXIT_CODE" -ne 0 ] || [ "$SEAM_EXIT" -ne 0 ]; then
  exit 1
fi
exit 0
