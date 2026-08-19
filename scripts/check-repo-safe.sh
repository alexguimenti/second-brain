#!/usr/bin/env bash
# Safety guard: blocks the specific failure modes that have actually bitten
# this repo. Reads its rules from scripts/repo-safety.config.json — edit that
# file when a new sensitive term appears, not this script.
#
# Two modes:
#   (no args)     Pre-commit mode — scans staged added lines only. Installed
#                 as .git/hooks/pre-commit by scripts/install.sh.
#   --tree <dir>  Full-tree mode — scans every file under <dir>. Used by
#                 scripts/build-public-snapshot.sh as the final gate before
#                 pushing a sanitized snapshot — this is what would have
#                 caught a real example name once accidentally baked into an
#                 early draft of this very script, since the ID->name shape
#                 pattern matches it regardless of whether the exact string
#                 was ever explicitly listed anywhere.
#
# Config file: <repo_root>/scripts/repo-safety.config.json
# (forbidden_patterns apply to both modes; public_only_checks apply only to
# --tree mode — broader term checks, e.g. company name and product codenames,
# that would be too noisy to block every commit but must never survive into
# a public snapshot).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG="$SCRIPT_DIR/repo-safety.config.json"

if [ ! -f "$CONFIG" ]; then
  echo "error: $CONFIG not found." >&2
  echo "Copy scripts/repo-safety.config.example.json to scripts/repo-safety.config.json" >&2
  echo "and fill in your own project's sensitive terms (run scripts/install.sh to do this automatically)." >&2
  exit 1
fi

FAIL=0
MODE="diff"
SCAN_DIR=""

if [ "${1:-}" = "--tree" ]; then
  MODE="tree"
  SCAN_DIR="${2:?--tree requires a directory argument}"
fi

if [ "$MODE" = "diff" ]; then
  # Staged added lines, excluding this file's own source and the config files
  # (whose regexes/examples necessarily contain fragments of what they match).
  CONTENT=$(git diff --cached -U0 -- . ':(exclude)scripts/check-repo-safe.sh' ':(exclude)scripts/repo-safety.config.json' ':(exclude)scripts/repo-safety.config.example.json' | grep -E '^\+[^+]' || true)
else
  CONTENT=$(grep -rInE '.' "$SCAN_DIR" \
    --exclude-dir=.git \
    --exclude=check-repo-safe.sh \
    --exclude=repo-safety.config.json \
    --exclude=repo-safety.config.example.json \
    2>/dev/null || true)
fi

# Read forbidden_patterns as TSV (label<TAB>regex) from the JSON config.
# In --tree mode, also load public_only_checks — broader term checks that
# would be too noisy for every commit (they'd flag normal, expected content
# in origin/gitlab) but must never survive into the public snapshot.
PATTERNS=$(python3 -c "
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    cfg = json.load(f)
for p in cfg['forbidden_patterns']:
    print(f\"{p['label']}\t{p['regex']}\")
if sys.argv[2] == 'tree':
    for p in cfg.get('public_only_checks', []):
        print(f\"{p['label']}\t{p['regex']}\")
" "$CONFIG" "$MODE")

while IFS=$'\t' read -r label pattern; do
  [ -z "$pattern" ] && continue
  hits=$(echo "$CONTENT" | grep -inE "$pattern" || true)
  if [ -n "$hits" ]; then
    echo "❌ BLOCKED — $label:"
    echo "$hits" | sed 's/^/    /'
    FAIL=1
  fi
done <<< "$PATTERNS"

# .env files: only meaningful in diff mode (staged file names).
if [ "$MODE" = "diff" ]; then
  ENV_FILES=$(git diff --cached --name-only | grep -E '(^|/)\.env$' || true)
  if [ -n "$ENV_FILES" ]; then
    echo "❌ BLOCKED — .env file staged (should be gitignored):"
    echo "$ENV_FILES" | sed 's/^/    /'
    FAIL=1
  fi
fi

if [ "$FAIL" -ne 0 ]; then
  echo ""
  if [ "$MODE" = "diff" ]; then
    echo "Commit blocked by scripts/check-repo-safe.sh. If this is a genuine false"
    echo "positive, fix the pattern in scripts/repo-safety.config.json rather than"
    echo "bypassing with --no-verify — there's no filtering step after this one"
    echo "before your remotes go live."
  else
    echo "Public snapshot build blocked by scripts/check-repo-safe.sh --tree."
    echo "Fix the flagged content in the temp clone (or add a translation to"
    echo "public_replacements in scripts/repo-safety.config.json) before pushing."
  fi
  exit 1
fi

exit 0
