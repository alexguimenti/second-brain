#!/usr/bin/env bash
# Rebuild the public showcase snapshot (the "public" remote) from the current
# repo state, fully automated: clone -> exclude -> sanitize -> verify -> push.
#
# Reads scripts/repo-safety.config.json for what to exclude/replace, and
# reuses scripts/check-repo-safe.sh as the final safety gate (full-tree mode)
# before anything is pushed. Never touches this repo's real working tree —
# all sanitization happens in a disposable temp clone.
#
# Usage:
#   bash scripts/build-public-snapshot.sh [public-remote-url]
#
# If no URL is given, uses the existing "public" remote's URL if one is
# configured in this repo.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
CONFIG="$SCRIPT_DIR/repo-safety.config.json"

PUBLIC_URL="${1:-}"
if [ -z "$PUBLIC_URL" ]; then
  PUBLIC_URL=$(git -C "$REPO_ROOT" remote get-url public 2>/dev/null || true)
fi
if [ -z "$PUBLIC_URL" ]; then
  echo "error: no public remote URL given and no 'public' remote configured." >&2
  echo "Usage: bash scripts/build-public-snapshot.sh <public-repo-url>" >&2
  exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "▶ Cloning current state into $TMP_DIR..."
git clone --depth 1 "file://$REPO_ROOT" "$TMP_DIR" >/dev/null 2>&1
rm -rf "$TMP_DIR/.git"

echo "▶ Removing excluded files..."
python3 -c "
import json, os, sys
with open(sys.argv[1], encoding='utf-8') as f:
    cfg = json.load(f)
tmp_dir = sys.argv[2]
for rel_path in cfg['public_exclude_files']:
    full = os.path.join(tmp_dir, rel_path)
    if os.path.exists(full):
        os.remove(full)
        print(f'  removed {rel_path}')
    else:
        print(f'  (already absent) {rel_path}')
" "$CONFIG" "$TMP_DIR"

echo "▶ Applying sanitization replacements..."
python3 -c "
import json, os, sys

config_path, tmp_dir = sys.argv[1], sys.argv[2]
with open(config_path, encoding='utf-8') as f:
    cfg = json.load(f)
replacements = [(r['from'], r['to']) for r in cfg['public_replacements']]

changed_files = 0
for root, dirs, files in os.walk(tmp_dir):
    dirs[:] = [d for d in dirs if d != '.git']
    for name in files:
        path = os.path.join(root, name)
        try:
            with open(path, encoding='utf-8') as f:
                content = f.read()
        except (UnicodeDecodeError, IsADirectoryError):
            continue  # binary or unreadable — leave as-is
        original = content
        for src, dst in replacements:
            content = content.replace(src, dst)
        if content != original:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            changed_files += 1
print(f'  {changed_files} files modified')
" "$CONFIG" "$TMP_DIR"

echo "▶ Running safety gate (full-tree scan)..."
if ! bash "$SCRIPT_DIR/check-repo-safe.sh" --tree "$TMP_DIR"; then
  echo ""
  echo "❌ Build ABORTED — safety gate found something. Nothing was pushed."
  echo "   Fix scripts/repo-safety.config.json (add a replacement or exclusion)"
  echo "   and re-run this script."
  exit 1
fi

echo "▶ Safety gate passed. Building single clean commit..."
(
  cd "$TMP_DIR"
  git init -b main >/dev/null
  git add -A
  git commit -q -m "Public showcase snapshot — $(date '+%Y-%m-%d')

Sanitized from the current repo state via scripts/build-public-snapshot.sh
(company name, product codenames, and real identifiers replaced with
generic placeholders per scripts/repo-safety.config.json)."
)

echo ""
echo "Ready to force-push to: $PUBLIC_URL"
read -r -p "Proceed with force-push? [y/N] " CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
  echo "Aborted — nothing pushed. Temp clone will still be cleaned up."
  exit 0
fi

(
  cd "$TMP_DIR"
  git remote add public "$PUBLIC_URL"
  git push --force public main
)

echo "✅ Public snapshot pushed."
