#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_ROOT="${VAULT_ROOT:-$HOME/Documents/Vaults/Mex_Vault}"
COMMANDS_DIR="$HOME/.claude/commands"

echo "Second Brain — Install"
echo "======================"
echo "Repo:     $REPO_ROOT"
echo "Vault:    $VAULT_ROOT"
echo "Commands: $COMMANDS_DIR"
echo ""

# 1. Deploy slash commands (substitute {{VAULT_ROOT}} placeholder with actual path)
echo "Deploying commands..."
mkdir -p "$COMMANDS_DIR"

# Resolve vault path to OS-native format for commands
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
  VAULT_PATH_NATIVE=$(cygpath -w "$VAULT_ROOT" 2>/dev/null || echo "$VAULT_ROOT")
else
  VAULT_PATH_NATIVE="$VAULT_ROOT"
fi

# Escape backslashes for sed replacement (Windows paths have backslashes)
VAULT_PATH_ESCAPED="${VAULT_PATH_NATIVE//\\/\\\\}"

for cmd in "$REPO_ROOT"/commands/*.md; do
  sed "s|{{VAULT_ROOT}}|${VAULT_PATH_ESCAPED}|g" "$cmd" > "$COMMANDS_DIR/$(basename "$cmd")"
  echo "  Deployed $(basename "$cmd")"
done

# 2. Create vault directory structure (if vault root exists)
if [ -d "$VAULT_ROOT" ]; then
  echo ""
  echo "Setting up vault directories..."
  mkdir -p "$VAULT_ROOT/Work/ClickUp"
  mkdir -p "$VAULT_ROOT/Work/Claude Code/Sessions"
  mkdir -p "$VAULT_ROOT/Work/EOD"
  mkdir -p "$VAULT_ROOT/Personal"
  mkdir -p "$VAULT_ROOT/Tools"
  echo "  Created Work/ClickUp/, Work/Claude Code/Sessions/, Work/EOD/, Personal/, Tools/"

  # 3. Copy sync config template (never overwrite existing)
  SYNC_CONFIG="$VAULT_ROOT/Work/ClickUp/sync-config.json"
  if [ ! -f "$SYNC_CONFIG" ]; then
    cp "$REPO_ROOT/config/sync-config.template.json" "$SYNC_CONFIG"
    echo "  Created sync-config.json from template"
  else
    echo "  sync-config.json already exists, skipping"
  fi
else
  echo ""
  echo "Vault root not found at $VAULT_ROOT — skipping vault setup."
  echo "Set VAULT_ROOT env var to your Obsidian vault path and re-run."
fi

# 4. QMD setup (optional — requires Node.js >= 22)
echo ""
if command -v qmd &> /dev/null; then
  echo "QMD detected. Run 'bash scripts/setup-qmd.sh' to update embeddings."
elif command -v node &> /dev/null; then
  NODE_VERSION=$(node -v | sed 's/v//' | cut -d. -f1)
  if [ "$NODE_VERSION" -ge 22 ]; then
    echo "Node.js >= 22 detected. For semantic search, run: bash scripts/setup-qmd.sh"
  else
    echo "QMD requires Node.js >= 22 (current: $(node -v)). Skipping semantic search setup."
  fi
else
  echo "QMD requires Node.js >= 22. Install Node.js for semantic search support."
fi

echo ""
echo "Done. Test with: /vault --types"
