#!/usr/bin/env bash
set -euo pipefail

VAULT_ROOT="${VAULT_ROOT:-$HOME/Documents/Vaults/Mex_Vault}"

echo "Second Brain — QMD Setup"
echo "========================"
echo "Vault: $VAULT_ROOT"
echo ""

# 1. Check Node.js >= 22
NODE_VERSION=$(node -v 2>/dev/null | sed 's/v//' | cut -d. -f1)
if [ -z "$NODE_VERSION" ] || [ "$NODE_VERSION" -lt 22 ]; then
  echo "ERROR: Node.js >= 22 required. Current: $(node -v 2>/dev/null || echo 'not installed')"
  echo "Install from https://nodejs.org/ or use nvm: nvm install 22"
  exit 1
fi

# 2. Install QMD globally if not present
if ! command -v qmd &> /dev/null; then
  echo "Installing QMD..."
  npm install -g @tobilu/qmd
  echo "  QMD installed"
else
  echo "QMD already installed: $(qmd --version 2>/dev/null || echo 'unknown version')"
fi

# 3. Register vault as a QMD collection
echo ""
echo "Registering vault collection..."
if qmd collection list 2>/dev/null | grep -q '\bvault\b'; then
  echo "  Collection 'vault' already registered — skipping"
else
  qmd collection add "$VAULT_ROOT" --name vault
  echo "  Collection 'vault' registered"
fi

# 4. Add context metadata per folder for better ranking
echo ""
echo "Adding context metadata..."
qmd context add qmd://vault "Personal knowledge vault — Obsidian notes, ClickUp docs, session logs, project specs"
qmd context add qmd://vault/Work/ClickUp "Synced ClickUp documents — product specs, engineering plans, reliability docs"
qmd context add qmd://vault/Work/Claude\ Code/Sessions "Claude Code session summaries — decisions, outcomes, resume commands"
qmd context add qmd://vault/Work/EOD "End-of-day summaries — daily progress recaps"
qmd context add qmd://vault/Work/Search\ Atlas "Search Atlas project documentation"
qmd context add qmd://vault/Personal "Personal notes and references"
qmd context add qmd://vault/Tools "Tool design documents and specs"
echo "  Context metadata added for all vault folders"

# 5. Run initial embedding
echo ""
echo "Running initial embedding (this may take a few minutes on first run)..."
echo "  Models will be downloaded to ~/.cache/qmd/models/ (~1.9GB)"
qmd embed
echo "  Embedding complete"

# 6. Verify
echo ""
echo "Verifying setup..."
qmd status
echo ""
echo "QMD setup complete. Test with: qmd query \"test search\""
echo ""
echo "Next steps:"
echo "  1. Add QMD MCP server to Claude Code settings (see docs/setup.md)"
echo "  2. Re-deploy commands: bash scripts/install.sh"
