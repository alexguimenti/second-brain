#!/usr/bin/env python3
"""Convert raw ClickUp chat JSON files to markdown snapshots.

Phase 2 of the two-phase chat sync:
  Phase 1: Claude (haiku) fetches messages via MCP → saves JSON to temp dir
  Phase 2: This script converts JSON → markdown (zero LLM tokens)

Usage:
    python scripts/convert-chat-json.py <json_dir>

Where <json_dir> contains files named <channel_id>.json, each with the raw
MCP response: {"messages": [...], "total_count": N, ...}
"""

import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", Path.home() / "Documents" / "Vaults" / "MyVault"))
CONFIG_PATH = VAULT_ROOT / "Work" / "ClickUp" / "chat-sync-config.json"
TZ = timezone(timedelta(hours=-3))

def load_user_map() -> dict:
    """Load the ClickUp user-ID -> display-name map from a local, gitignored
    file next to this script. Never hardcode real names here — see
    SECURITY.md. Copy scripts/chat-user-map.example.json to
    scripts/convert-chat-json.usermap.json and fill in your own roster."""
    map_path = Path(__file__).with_name("convert-chat-json.usermap.json")
    if map_path.exists():
        return json.loads(map_path.read_text(encoding="utf-8"))
    return {}


USER_MAP = load_user_map()


def clean_mentions(text: str) -> str:
    # [@Name](#user_mention#id) → @Name
    text = re.sub(r'\[@([^\]]+)\]\(#user_mention#\d+\)', r'@\1', text)
    # [](#user_group_mention#id) → @team
    text = re.sub(r'\[([^\]]*)\]\(#user_group_mention#[^)]+\)', lambda m: m.group(1) if m.group(1) else '@team', text)
    # [@followers](#task_user_group_mention#followers_tag) → @followers
    text = re.sub(r'\[@followers\]\(#task_user_group_mention#followers_tag\)', '@followers', text)
    return text


def format_timestamp(epoch_ms: int) -> str:
    dt = datetime.fromtimestamp(epoch_ms / 1000, tz=TZ)
    return dt.strftime("%Y-%m-%d %H:%M")


def resolve_author(user_id) -> str:
    return USER_MAP.get(str(user_id), f"User {user_id}")


def write_snapshot(channel: dict, messages: list):
    name = channel["name"]
    channel_id = channel["channel_id"]
    vault_file = channel["vault_file"]
    filepath = VAULT_ROOT / vault_file

    filepath.parent.mkdir(parents=True, exist_ok=True)

    # Reverse: API returns newest first, we want oldest first
    messages = list(reversed(messages))
    count = len(messages)
    now = datetime.now(tz=TZ).strftime("%Y-%m-%dT%H:%M:%S%z")
    now_short = datetime.now(tz=TZ).strftime("%Y-%m-%d %H:%M")

    lines = [
        "---",
        "type: clickup-chat",
        f"channel: {name}",
        f"channel_id: {channel_id}",
        f"last_synced: {now}",
        f"message_count: {count}",
        "---",
        "",
        f"# ClickUp Chat — {name}",
        "",
        f"*Last synced: {now_short} · Showing last {count} messages*",
        "",
    ]

    for msg in messages:
        author = resolve_author(msg.get("user_id", ""))
        ts = format_timestamp(msg["date"])
        content = clean_mentions(msg.get("content", ""))
        if not content.strip():
            content = "*(empty message)*"
        lines.append("---")
        lines.append("")
        lines.append(f"**{author}** · {ts}")
        lines.append(content)
        lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return count


def main():
    if len(sys.argv) < 2:
        print("Usage: python convert-chat-json.py <json_dir>", file=sys.stderr)
        sys.exit(1)

    json_dir = Path(sys.argv[1])
    if not json_dir.exists():
        print(f"ERROR: Directory {json_dir} not found", file=sys.stderr)
        sys.exit(1)

    config = json.loads(CONFIG_PATH.read_text())
    channel_map = {ch["channel_id"]: ch for ch in config["channels"]}

    written = 0
    skipped = 0

    for json_file in sorted(json_dir.glob("*.json")):
        channel_id = json_file.stem
        if channel_id not in channel_map:
            print(f"  SKIP {json_file.name} — not in config")
            skipped += 1
            continue

        data = json.loads(json_file.read_text())
        messages = data.get("messages", [])
        if not messages:
            print(f"  SKIP {channel_id} — no messages")
            skipped += 1
            continue

        ch = channel_map[channel_id]
        count = write_snapshot(ch, messages)
        print(f"  OK {ch['name']}: {count} messages → {ch['vault_file']}")
        written += 1

    print(f"\nDone: {written} written, {skipped} skipped")


if __name__ == "__main__":
    main()
