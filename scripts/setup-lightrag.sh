#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
LIGHTRAG_DIR="$REPO_ROOT/lightrag"
VAULT_ROOT="${VAULT_ROOT:-$HOME/Documents/Vaults/Mex_Vault}"
MGMT_ENV="$HOME/Documents/Projects/search_atlas/mgmt/.env"

echo "Second Brain — LightRAG Setup"
echo "=============================="
echo "LightRAG dir: $LIGHTRAG_DIR"
echo "Vault:        $VAULT_ROOT"
echo ""

# 1. Check Docker
if ! command -v docker &> /dev/null; then
  echo "ERROR: Docker not found. Install Docker Desktop first."
  exit 1
fi
echo "Docker: $(docker --version)"

# 2. Create data directories
mkdir -p "$LIGHTRAG_DIR/data/rag_storage"
mkdir -p "$LIGHTRAG_DIR/data/inputs"
echo "Created data directories"

# 3. Create .env from template + OpenAI key from mgmt
if [ ! -f "$LIGHTRAG_DIR/.env" ]; then
  if [ -f "$MGMT_ENV" ]; then
    OPENAI_KEY=$(grep "^OPENAI_API_KEY=" "$MGMT_ENV" | cut -d'=' -f2-)
    if [ -n "$OPENAI_KEY" ]; then
      sed "s/your-openai-api-key-here/$OPENAI_KEY/g" "$LIGHTRAG_DIR/.env.template" > "$LIGHTRAG_DIR/.env"
      echo "Created .env with OpenAI key from mgmt/.env"
    else
      cp "$LIGHTRAG_DIR/.env.template" "$LIGHTRAG_DIR/.env"
      echo "WARNING: No OPENAI_API_KEY found in mgmt/.env. Edit lightrag/.env manually."
    fi
  else
    cp "$LIGHTRAG_DIR/.env.template" "$LIGHTRAG_DIR/.env"
    echo "WARNING: mgmt/.env not found. Edit lightrag/.env manually."
  fi
else
  echo ".env already exists, skipping"
fi

# 4. Start LightRAG
echo ""
echo "Starting LightRAG..."
cd "$LIGHTRAG_DIR"
docker compose up -d

echo ""
echo "Waiting for LightRAG to be ready..."
for i in $(seq 1 30); do
  if curl -s http://localhost:9621/health > /dev/null 2>&1; then
    echo "LightRAG is ready at http://localhost:9621"
    break
  fi
  sleep 2
done

# 5. Index vault files
echo ""
echo "Indexing vault files..."
TOTAL=0
SKIPPED=0

# Copy linkable content to inputs directory (skip prompts, configs, auto-backups)
find "$VAULT_ROOT/Work/ClickUp" -name "*.md" -not -path "*/Chat/*" 2>/dev/null | while read f; do
  cp "$f" "$LIGHTRAG_DIR/data/inputs/"
  TOTAL=$((TOTAL + 1))
done

find "$VAULT_ROOT/Work/Claude Code/Sessions" -name "*.md" -not -path "*/auto/*" 2>/dev/null | while read f; do
  cp "$f" "$LIGHTRAG_DIR/data/inputs/"
done

find "$VAULT_ROOT/Work/EOD" -name "*.md" 2>/dev/null | while read f; do
  cp "$f" "$LIGHTRAG_DIR/data/inputs/"
done

find "$VAULT_ROOT/Work/Search Atlas" -name "*.md" 2>/dev/null | while read f; do
  cp "$f" "$LIGHTRAG_DIR/data/inputs/"
done

# Copy global memory files
for f in USER.md SOUL.md MEMORY.md; do
  [ -f "$VAULT_ROOT/Tools/$f" ] && cp "$VAULT_ROOT/Tools/$f" "$LIGHTRAG_DIR/data/inputs/"
done

FILE_COUNT=$(ls "$LIGHTRAG_DIR/data/inputs/"*.md 2>/dev/null | wc -l)
echo "Copied $FILE_COUNT files to inputs directory"

# Trigger scan
echo "Triggering document scan..."
curl -s -X POST http://localhost:9621/documents/scan | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Scan started. Track: {d}')" 2>/dev/null || echo "Scan triggered"

echo ""
echo "LightRAG setup complete!"
echo ""
echo "  Web UI:    http://localhost:9621/webui"
echo "  API docs:  http://localhost:9621/docs"
echo "  Health:    http://localhost:9621/health"
echo ""
echo "Indexing is running in the background. Check progress:"
echo "  curl http://localhost:9621/documents/status_counts"
echo ""
echo "Test a query:"
echo '  curl -X POST http://localhost:9621/query -H "Content-Type: application/json" -d '"'"'{"query":"reliability plan","mode":"hybrid"}'"'"''
