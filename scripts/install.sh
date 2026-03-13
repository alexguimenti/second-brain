#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
VAULT_ROOT="${VAULT_ROOT:-$HOME/Documents/Vault}"
COMMANDS_DIR="$HOME/.claude/commands"

echo "Second Brain — Install"
echo "======================"
echo "Repo:     $REPO_ROOT"
echo "Vault:    $VAULT_ROOT"
echo "Commands: $COMMANDS_DIR"
echo ""

# 1. Deploy slash commands
echo "Deploying commands..."
mkdir -p "$COMMANDS_DIR"
for cmd in "$REPO_ROOT"/commands/*.md; do
  cp "$cmd" "$COMMANDS_DIR/"
  echo "  Copied $(basename "$cmd")"
done

# 2. Create vault directory structure (if vault root exists)
if [ -d "$VAULT_ROOT" ]; then
  echo ""
  echo "Setting up vault directories..."
  mkdir -p "$VAULT_ROOT/ClickUp"
  mkdir -p "$VAULT_ROOT/Claude Code/Sessions"
  mkdir -p "$VAULT_ROOT/Claude Code/Tools"
  echo "  Created ClickUp/, Claude Code/Sessions/, Claude Code/Tools/"

  # 3. Copy sync config template (never overwrite existing)
  SYNC_CONFIG="$VAULT_ROOT/ClickUp/sync-config.json"
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

echo ""
echo "Done. Test with: /vault --types"
