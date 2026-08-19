#!/usr/bin/env python3
"""Convert ClickUp chat JSON to Obsidian vault markdown snapshots."""
import json, sys, os
from datetime import datetime, timezone
from pathlib import Path


def load_user_map() -> dict:
    """Load the ClickUp user-ID -> display-name map from a local, gitignored
    file next to this script. Never hardcode real names here — see
    SECURITY.md. Copy scripts/chat-user-map.example.json to
    scripts/chat-snapshot.usermap.json and fill in your own roster."""
    map_path = Path(__file__).with_name("chat-snapshot.usermap.json")
    if map_path.exists():
        return json.loads(map_path.read_text(encoding="utf-8"))
    return {}


USER_MAP = load_user_map()

import re

def clean_mentions(text):
    # [@Name](#user_mention#id) -> @Name
    text = re.sub(r'\[@([^\]]+)\]\(#user_mention#[^)]+\)', r'@\1', text)
    # [](#user_group_mention#id) -> @team
    text = re.sub(r'\[([^\]]*)\]\(#user_group_mention#[^)]+\)', lambda m: m.group(1) if m.group(1) else '@team', text)
    # [@followers](#task_user_group_mention#followers_tag) -> @followers
    text = re.sub(r'\[@followers\]\(#task_user_group_mention#[^)]+\)', '@followers', text)
    # Also handle the format without brackets for group mentions
    text = re.sub(r'\[\]\(#user_group_mention#[^)]+\)', '@team', text)
    return text

def epoch_to_str(epoch_ms):
    dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")

def process_channel(json_path, channel_name, channel_id, output_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    messages = data.get("messages", [])
    # Reverse to chronological (oldest first)
    messages.sort(key=lambda m: m["date"])

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    now_short = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    count = len(messages)

    lines = [
        "---",
        "type: clickup-chat",
        f"channel: {channel_name}",
        f"channel_id: {channel_id}",
        f"last_synced: {now}",
        f"message_count: {count}",
        "---",
        "",
        f"# ClickUp Chat — {channel_name}",
        "",
        f"*Last synced: {now_short} · Showing last {count} messages*",
        "",
    ]

    for msg in messages:
        user_id = str(msg.get("user_id", ""))
        author = USER_MAP.get(user_id, f"User {user_id}")
        timestamp = epoch_to_str(msg["date"])
        content = clean_mentions(msg.get("content", ""))

        if not content.strip():
            continue

        lines.append("---")
        lines.append("")
        lines.append(f"**{author}** · {timestamp}")
        lines.append(content)
        lines.append("")

    lines.append("---")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"Wrote {count} messages to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: chat-snapshot.py <json_path> <channel_name> <channel_id> <output_path>")
        sys.exit(1)

    process_channel(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
